import asyncio
import gc
import json
import math
import os
import random
import statistics
import tempfile
import time
import unittest
import sys
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.perception.socket_reader import SocketReader, normalize_address, parse_event_line
from src.perception.ipc_server import IPCServer

class TestSocketReaderStress(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.reader = SocketReader()

    def test_rapid_1000_event_lines(self):
        events = []
        for i in range(1000):
            mod = i % 10
            if mod == 0:
                events.append(f"openwindow>>0x5616a030{i:04x},1,foot,Terminal {i}\n")
            elif mod == 1:
                events.append(f"closewindow>>0x5616a030{i:04x}\n")
            elif mod == 2:
                events.append(f"movewindow>>0x5616a030{i:04x},workspace_{i % 5}\n")
            elif mod == 3:
                events.append(f"movewindowv2>>0x5616a030{i:04x},{i % 5},workspace_{i % 5}\n")
            elif mod == 4:
                events.append(f"activewindow>>foot,Terminal {i}\n")
            elif mod == 5:
                events.append(f"activewindowv2>>0x5616a030{i:04x}\n")
            elif mod == 6:
                events.append(f"changefloatingmode>>0x5616a030{i:04x},{i % 2}\n")
            elif mod == 7:
                events.append(f"fullscreen>>{i % 2}\n")
            elif mod == 8:
                events.append(f"pin>>0x5616a030{i:04x},{i % 2}\n")
            else:
                events.append(f"windowtitlev2>>0x5616a030{i:04x},Window Title {i}\n")

        q = self.reader.create_queue(maxsize=2000)
        captured = []
        self.reader.add_callback(lambda ev: captured.append(ev))

        payload = "".join(events)
        t_start = time.perf_counter()
        parsed = self.reader.feed_data(payload)
        t_elapsed = time.perf_counter() - t_start

        self.assertEqual(len(parsed), 1000)
        self.assertEqual(len(captured), 1000)
        self.assertEqual(q.qsize(), 1000)
        self.assertTrue(self.reader.is_geometry_dirty)

        throughput = 1000.0 / t_elapsed
        latency_us = (t_elapsed / 1000.0) * 1e6
        print(f"\n[STRESS M1.1] Rapid 1,000 Events: {throughput:.1f} events/s, Latency: {latency_us:.2f} us/event")
        self.assertGreater(throughput, 5000.0)
        self.assertLess(latency_us, 200.0)

    def test_extreme_single_byte_fragmentation(self):
        events = []
        for i in range(1000):
            events.append(f"openwindow>>0xbeef{i:04x},1,class{i},title{i}\n")
        full_stream = "".join(events)

        t_start = time.perf_counter()
        total_parsed = 0
        for char in full_stream:
            res = self.reader.feed_data(char)
            total_parsed += len(res)
        t_elapsed = time.perf_counter() - t_start

        self.assertEqual(total_parsed, 1000)
        self.assertEqual(len(self.reader.events_received), 1000)
        self.assertEqual(self.reader.buffer, "")

        throughput = 1000.0 / t_elapsed
        print(f"[STRESS M1.1] 1-Byte Chunks (len={len(full_stream)}): {throughput:.1f} events/s ({t_elapsed:.3f}s)")
        self.assertGreater(total_parsed, 999)

    def test_variable_prime_fragmentation(self):
        events = []
        for i in range(1000):
            events.append(f"movewindowv2>>0xcafe{i:04x},{i % 4},ws_{i % 4}\n")
        full_stream = "".join(events)

        chunk_sizes = [2, 3, 5, 7, 11, 13, 17, 23, 29, 31, 47, 61, 97, 127]
        idx = 0
        chunk_ptr = 0
        total_parsed = 0

        t_start = time.perf_counter()
        while idx < len(full_stream):
            sz = chunk_sizes[chunk_ptr % len(chunk_sizes)]
            chunk_ptr += 1
            chunk = full_stream[idx : idx + sz]
            idx += sz
            res = self.reader.feed_data(chunk)
            total_parsed += len(res)
        t_elapsed = time.perf_counter() - t_start

        self.assertEqual(total_parsed, 1000)
        self.assertEqual(len(self.reader.events_received), 1000)
        self.assertEqual(self.reader.buffer, "")
        print(f"[STRESS M1.1] Variable Prime Chunks: 1,000 events delivered ({t_elapsed:.3f}s)")

    async def test_stream_reader_pipeline_fragmented(self):
        stream_reader = asyncio.StreamReader()
        run_task = asyncio.create_task(self.reader.run_stream(stream_reader))

        events = []
        for i in range(1000):
            events.append(f"closewindow>>0xdead{i:04x}\n")
        raw_bytes = "".join(events).encode("utf-8")

        chunk_size = 19
        for start in range(0, len(raw_bytes), chunk_size):
            chunk = raw_bytes[start : start + chunk_size]
            stream_reader.feed_data(chunk)
            await asyncio.sleep(0.00001)

        stream_reader.feed_eof()
        await run_task

        self.assertEqual(len(self.reader.events_received), 1000)
        print(f"[STRESS M1.1] Async Stream Pipeline: 1,000 events parsed across 19-byte TCP frames")

    def test_malformed_and_adversarial_stream_resilience(self):
        adversarial_corpus = [
            "completely malformed without separator\n",
            "\n",
            "   \n",
            "\r\n",
            ">>\n",
            ">>only_data\n",
            "only_event>>\n",
            ">>>>multiple>>delimiters>>everywhere\n",
            "openwindow>>\n",
            "openwindow>>,,\n",
            "openwindow>>not_hex,not_num,,\n",
            "movewindowv2>>not_an_int,neither\n",
            "workspacev2>>not_an_int\n",
            "focusedmonv2>>mon,not_an_int\n",
            "pin>>0x123,not_a_bool\n",
            "minimized>>0x123,not_a_bool\n",
            "openwindow>>" + ("Z" * 50000) + ",1,cls,title\n",
            "openwindow>>0x123,1,cls,null\x00byte\n",
            "openwindow>>0xabc,2,terminal,unicode_rocket_🚀_fire_🔥\n",
            "activewindowv2>>  0XABCDEF  \n",
            "closewindow>>   \n",
        ]

        valid_counter = 0
        feed_stream = []
        for i in range(250):
            feed_stream.append(adversarial_corpus[i % len(adversarial_corpus)])
            feed_stream.append(f"openwindow>>0x1000{i:04x},1,safe_class,safe_title_{i}\n")
            valid_counter += 1

        combined = "".join(feed_stream)
        t_start = time.perf_counter()
        parsed = self.reader.feed_data(combined)
        t_elapsed = time.perf_counter() - t_start

        valid_events = [e for e in parsed if e.get("event") == "openwindow" and e.get("window_class") == "safe_class"]
        self.assertEqual(len(valid_events), 250)
        self.assertTrue(self.reader.is_geometry_dirty)
        print(f"[STRESS M1.1] Adversarial Stream Resilience: 250 corrupted frames handled without crash ({t_elapsed:.3f}s)")

    async def test_dynamic_reconnect_resilience(self):
        tmp_dir = tempfile.mkdtemp()
        sock_path = os.path.join(tmp_dir, f"test_hypr_{os.getpid()}_{int(time.time()*1000)}.sock")
        reader = SocketReader(socket_path=sock_path, reconnect_delay=0.02, max_reconnect_delay=0.05)
        await reader.start()
        self.assertFalse(reader.is_connected)

        keep_alive = asyncio.Event()

        async def dummy_cb(r, w):
            w.write(b"openwindow>>0x999,1,kitty,term\n")
            await w.drain()
            await keep_alive.wait()
            w.close()
            await w.wait_closed()

        srv = await asyncio.start_unix_server(dummy_cb, path=sock_path)
        await asyncio.sleep(0.08)
        self.assertTrue(reader.is_connected)

        keep_alive.set()
        srv.close()
        await srv.wait_closed()
        await asyncio.sleep(0.08)
        self.assertFalse(reader.is_connected)

        await reader.stop()
        if os.path.exists(sock_path):
            os.remove(sock_path)
        if os.path.exists(tmp_dir):
            os.rmdir(tmp_dir)
        print(f"[STRESS M1.1] Dynamic Reconnect: Socket appearance and disappearance handled cleanly")

    def test_memory_retention_profile(self):
        total_events = 10000
        batch_size = 1000
        t_start = time.perf_counter()
        for batch_idx in range(total_events // batch_size):
            chunk = "".join([f"openwindow>>0x{i:04x},1,class,title\n" for i in range(batch_size)])
            self.reader.feed_data(chunk)
        t_elapsed = time.perf_counter() - t_start
        self.assertEqual(len(self.reader.events_received), total_events)
        throughput = total_events / t_elapsed
        print(f"[STRESS M1.1] Memory Profile: {total_events} events stored in {t_elapsed:.3f}s ({throughput:.1f} events/s)")

class TestIPCServerStress(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.sock_path = os.path.join(self.tmp_dir, f"ipc_stress_{os.getpid()}_{int(time.time()*1000)}.sock")

    async def asyncTearDown(self):
        if os.path.exists(self.sock_path):
            try:
                os.remove(self.sock_path)
            except OSError:
                pass
        if os.path.exists(self.tmp_dir):
            try:
                os.rmdir(self.tmp_dir)
            except OSError:
                pass

    async def test_60hz_broadcast_with_10_clients(self):
        fps = 60.0
        frame_counter = 0

        async def frame_provider():
            nonlocal frame_counter
            frame_counter += 1
            t = time.time()
            return {
                "timestamp": t,
                "frame_idx": frame_counter,
                "cursor": {"x": int(500 + 100 * math.cos(t)), "y": int(400 + 100 * math.sin(t)), "z": 0.0},
                "active_window": {
                    "address": "0x5616a03008b0",
                    "title": "foot",
                    "class": "foot",
                    "at": [100, 150],
                    "size": [800, 600],
                    "workspace": 1,
                    "z_depth": 0.0,
                    "top_ledge": {"start": [100.0, 150.0, 0.0], "end": [900.0, 150.0, 0.0]},
                },
                "collision_planes": [
                    {
                        "id": "0x5616a03008b0",
                        "type": "window_top",
                        "plane": [0.0, 1.0, 0.0, -150.0],
                        "bounds": [100.0, 900.0, 150.0, 150.0, -0.1, 0.1],
                    }
                ],
                "action_feedback": {"last_action": "none", "status": "ok"},
            }

        server = IPCServer(
            socket_path=self.sock_path,
            fps=fps,
            frame_provider=frame_provider,
        )
        await server.start()

        num_clients = 10
        target_frames = 120
        clients_data: List[List[Tuple[float, Dict[str, Any]]]] = [[] for _ in range(num_clients)]
        client_writers: List[asyncio.StreamWriter] = []

        async def run_client(client_idx: int):
            reader, writer = await asyncio.open_unix_connection(self.sock_path)
            client_writers.append(writer)
            storage = clients_data[client_idx]
            while len(storage) < target_frames and server.running:
                try:
                    line = await asyncio.wait_for(reader.readline(), timeout=1.0)
                    if not line:
                        break
                    now_mono = time.monotonic()
                    parsed = json.loads(line.decode("utf-8").strip())
                    storage.append((now_mono, parsed))
                except (asyncio.TimeoutError, json.JSONDecodeError, ConnectionError):
                    break

        tasks = [asyncio.create_task(run_client(i)) for i in range(num_clients)]
        await asyncio.gather(*tasks)

        for w in client_writers:
            w.close()
            try:
                await w.wait_closed()
            except Exception:
                pass

        await server.stop()

        for c_idx, data in enumerate(clients_data):
            self.assertEqual(len(data), target_frames, f"Client {c_idx} dropped packets: received {len(data)}/{target_frames}")

        all_intervals = []
        for c_idx, data in enumerate(clients_data):
            ts_list = [item[0] for item in data]
            intervals = [ts_list[i] - ts_list[i - 1] for i in range(1, len(ts_list))]
            all_intervals.extend(intervals)

            for _, frame in data:
                self.assertIn("timestamp", frame)
                self.assertIn("cursor", frame)
                self.assertIn("active_window", frame)
                self.assertIn("collision_planes", frame)
                self.assertIn("action_feedback", frame)

        mean_interval = statistics.mean(all_intervals) * 1000.0
        jitter_stddev = statistics.stdev(all_intervals) * 1000.0
        min_interval = min(all_intervals) * 1000.0
        max_interval = max(all_intervals) * 1000.0
        sorted_intervals = sorted(all_intervals)
        p50_interval = sorted_intervals[int(len(sorted_intervals) * 0.50)] * 1000.0
        p95_interval = sorted_intervals[int(len(sorted_intervals) * 0.95)] * 1000.0
        p99_interval = sorted_intervals[int(len(sorted_intervals) * 0.99)] * 1000.0

        print(f"\n[STRESS M1.1] 60 Hz 10-Client Broadcast Benchmark:")
        print(f"  Clients: {num_clients} concurrent visual engine clients")
        print(f"  Total Frames Delivered: {num_clients * target_frames} (0% dropped)")
        print(f"  Nominal Interval: {1000.0 / fps:.3f} ms (60.0 Hz)")
        print(f"  Mean Interval: {mean_interval:.3f} ms")
        print(f"  Clock Jitter (StdDev): {jitter_stddev:.3f} ms")
        print(f"  Min / Max Interval: {min_interval:.3f} ms / {max_interval:.3f} ms")
        print(f"  P50 / P95 / P99: {p50_interval:.3f} ms / {p95_interval:.3f} ms / {p99_interval:.3f} ms")

        self.assertAlmostEqual(mean_interval, 16.67, delta=2.5)
        self.assertLess(jitter_stddev, 5.0)
        self.assertLess(p95_interval, 25.0)

    async def test_abrupt_client_disconnect_recovery(self):
        fps = 60.0

        async def frame_provider():
            return {
                "timestamp": time.time(),
                "cursor": {"x": 100, "y": 200, "z": 0.0},
                "active_window": {"address": "0x123"},
                "collision_planes": [],
                "action_feedback": {"status": "ok"},
            }

        server = IPCServer(
            socket_path=self.sock_path,
            fps=fps,
            frame_provider=frame_provider,
        )
        await server.start()

        num_clients = 10
        readers = []
        writers = []
        for _ in range(num_clients):
            r, w = await asyncio.open_unix_connection(self.sock_path)
            readers.append(r)
            writers.append(w)

        await asyncio.sleep(0.05)
        self.assertEqual(len(server.clients), 10)

        for i in range(4):
            writers[i].close()
            try:
                await writers[i].wait_closed()
            except Exception:
                pass

        await asyncio.sleep(0.1)

        surviving_data = []
        for i in range(4, 10):
            line = await asyncio.wait_for(readers[i].readline(), timeout=1.0)
            parsed = json.loads(line.decode("utf-8").strip())
            surviving_data.append(parsed)

        for i in range(4, 10):
            writers[i].close()
            try:
                await writers[i].wait_closed()
            except Exception:
                pass

        await server.stop()

        self.assertEqual(len(surviving_data), 6)
        print(f"[STRESS M1.1] Abrupt Disconnect Recovery: 4 clients killed, 6 surviving clients unaffected")

    async def test_bidirectional_control_under_load(self):
        fps = 60.0
        control_acks = []

        async def mock_control_handler(payload: Dict[str, Any]) -> Dict[str, Any]:
            cmd = payload.get("command", "")
            return {
                "status": "ok",
                "ack_id": payload.get("id", 0),
                "command": cmd,
                "delta_applied": payload.get("delta", [0, 0]),
            }

        server = IPCServer(
            socket_path=self.sock_path,
            fps=fps,
            frame_provider=lambda: asyncio.sleep(0, result={
                "timestamp": time.time(),
                "cursor": {"x": 300, "y": 400, "z": 0.0},
                "active_window": {"address": "0x5616a03008b0"},
                "collision_planes": [],
                "action_feedback": {"status": "ok"},
            }),
            control_handler=mock_control_handler,
        )
        await server.start()

        num_clients = 5
        readers = []
        writers = []
        for _ in range(num_clients):
            r, w = await asyncio.open_unix_connection(self.sock_path)
            readers.append(r)
            writers.append(w)

        await asyncio.sleep(0.05)

        total_commands = 200
        latencies = []
        malformed_errors = []

        async def send_and_receive(client_idx: int, command_batch: List[Dict[str, Any]]):
            r = readers[client_idx]
            w = writers[client_idx]
            for cmd in command_batch:
                t_sent = time.perf_counter()
                wire = json.dumps(cmd).encode("utf-8") + b"\n"
                w.write(wire)
                await w.drain()

                while True:
                    line = await asyncio.wait_for(r.readline(), timeout=1.0)
                    parsed = json.loads(line.decode("utf-8").strip())
                    if "status" in parsed:
                        t_ack = time.perf_counter()
                        latencies.append((t_ack - t_sent) * 1000.0)
                        control_acks.append(parsed)
                        break

        batches = [[] for _ in range(num_clients)]
        for i in range(total_commands):
            batches[i % num_clients].append({
                "id": i,
                "command": "push_window",
                "target_address": f"0x{i:04x}",
                "delta": [10, -5],
            })

        tasks = [asyncio.create_task(send_and_receive(i, batches[i])) for i in range(num_clients)]
        await asyncio.gather(*tasks)

        bad_writer = writers[0]
        bad_reader = readers[0]
        for _ in range(30):
            bad_writer.write(b'{"invalid_json_missing_brace": true\n')
            await bad_writer.drain()
            while True:
                line = await asyncio.wait_for(bad_reader.readline(), timeout=1.0)
                parsed = json.loads(line.decode("utf-8").strip())
                if "status" in parsed:
                    malformed_errors.append(parsed)
                    break

        for w in writers:
            w.close()
            try:
                await w.wait_closed()
            except Exception:
                pass

        await server.stop()

        self.assertEqual(len(control_acks), total_commands)
        self.assertEqual(len(malformed_errors), 30)
        for err in malformed_errors:
            self.assertEqual(err.get("status"), "error")
            self.assertEqual(err.get("message"), "invalid_json")

        mean_lat = statistics.mean(latencies)
        p95_lat = sorted(latencies)[int(len(latencies) * 0.95)]
        max_lat = max(latencies)

        print(f"[STRESS M1.1] Bidirectional Control Under Load:")
        print(f"  Commands Processed: {len(control_acks)} / {total_commands} (100% success)")
        print(f"  Malformed Injections Handled: {len(malformed_errors)} / 30 error replies")
        print(f"  Round-trip Latency: Mean {mean_lat:.3f} ms, P95 {p95_lat:.3f} ms, Max {max_lat:.3f} ms")

        self.assertLess(mean_lat, 10.0)
        self.assertLess(p95_lat, 20.0)

    async def test_slow_client_backpressure_threshold(self):
        fps = 60.0
        server = IPCServer(socket_path=self.sock_path, fps=fps)
        await server.start()

        r_fast, w_fast = await asyncio.open_unix_connection(self.sock_path)
        r_slow, w_slow = await asyncio.open_unix_connection(self.sock_path)
        await asyncio.sleep(0.05)

        frame = server.build_telemetry_packet()
        buffered_frames = 0
        backpressure_detected = False

        for _ in range(1200):
            try:
                await asyncio.wait_for(server.broadcast_frame(frame), timeout=0.1)
                await asyncio.wait_for(r_fast.readline(), timeout=0.05)
                buffered_frames += 1
            except asyncio.TimeoutError:
                backpressure_detected = True
                break

        w_fast.close()
        w_slow.close()
        try:
            await w_fast.wait_closed()
            await w_slow.wait_closed()
        except Exception:
            pass

        await server.stop()
        print(f"[STRESS M1.1] Slow Client Backpressure: Kernel socket buffer saturated after {buffered_frames} frames (detected={backpressure_detected})")

def main():
    unittest.main()

if __name__ == "__main__":
    main()
