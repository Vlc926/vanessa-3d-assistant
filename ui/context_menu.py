from PyQt6.QtWidgets import QMenu, QWidgetAction, QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt6.QtGui import QAction, QFont, QContextMenuEvent
from PyQt6.QtCore import Qt, QPoint

def get_context_menu_stylesheet() -> str:
    return """
        QMenu {
            background-color: rgba(22, 16, 34, 0.96);
            color: #fdf2f8;
            border: 1.5px solid rgba(255, 117, 160, 0.55);
            border-radius: 16px;
            padding: 8px 6px;
            font-family: 'Segoe UI', system-ui, sans-serif;
            font-size: 13px;
        }
        QMenu::item {
            padding: 8px 22px 8px 14px;
            border-radius: 9px;
            margin: 2px 4px;
            color: #f1e6f5;
        }
        QMenu::item:selected {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 rgba(255, 105, 155, 0.85),
                stop:0.6 rgba(217, 70, 139, 0.75),
                stop:1 rgba(147, 51, 234, 0.65));
            border-left: 3.5px solid #ff75a0;
            color: #ffffff;
            font-weight: 600;
        }
        QMenu::right-arrow {
            width: 0;
            height: 0;
            border-left: 6px solid #ff75a0;
            border-top: 4px solid transparent;
            border-bottom: 4px solid transparent;
            margin-right: 8px;
        }
        QMenu::right-arrow:selected {
            border-left: 6px solid #ffffff;
        }
        QMenu::separator {
            height: 1px;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 transparent,
                stop:0.5 rgba(255, 117, 160, 0.4),
                stop:1 transparent);
            margin: 6px 12px;
        }
    """

def build_context_menu(overlay) -> QMenu:
    menu = QMenu(overlay)
    menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
    menu_stylesheet = get_context_menu_stylesheet()
    menu.setStyleSheet(menu_stylesheet)

    header_action = QWidgetAction(menu)
    header_widget = QWidget()
    header_widget.setStyleSheet("background: transparent;")
    header_layout = QVBoxLayout(header_widget)
    header_layout.setContentsMargins(14, 10, 14, 8)
    header_layout.setSpacing(3)

    title_box = QHBoxLayout()
    title_box.setSpacing(6)
    icon_lbl = QLabel("🌸")
    icon_lbl.setStyleSheet("font-size: 16px;")
    title_lbl = QLabel("VANESSA 3D")
    title_lbl.setStyleSheet("color: #ff75a0; font-weight: 800; font-size: 14px; letter-spacing: 1.5px;")
    title_box.addWidget(icon_lbl)
    title_box.addWidget(title_lbl)
    title_box.addStretch()

    badge_lbl = QLabel("VRM • ARKit 52")
    badge_lbl.setStyleSheet("""
        background: rgba(255, 117, 160, 0.2);
        color: #ff94b8;
        border: 1px solid rgba(255, 117, 160, 0.5);
        border-radius: 5px;
        padding: 2px 7px;
        font-size: 10px;
        font-weight: 700;
    """)
    title_box.addWidget(badge_lbl)
    header_layout.addLayout(title_box)

    sub_lbl = QLabel("● Amo: Víctor • Guardiana Cognitiva • Control por Voz Activo")
    sub_lbl.setStyleSheet("color: #e2d9f3; font-size: 11px; font-weight: 500;")
    header_layout.addWidget(sub_lbl)

    header_action.setDefaultWidget(header_widget)
    menu.addAction(header_action)
    prot_mgr = getattr(overlay, "protection_protocol", None)
    if prot_mgr and getattr(prot_mgr, "is_active", False):
        act_prot = QAction(f"🛑 Desactivar Protocolo de Protección ({prot_mgr.formatted_remaining_time()})", overlay)
        act_prot.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        act_prot.triggered.connect(prot_mgr.deactivate_protocol)
        menu.addAction(act_prot)
    else:
        act_prot = QAction("🛡️ Activar Protocolo de Protección (Demo 5 min)", overlay)
        act_prot.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        if hasattr(overlay, "trigger_protection_protocol_demo"):
            act_prot.triggered.connect(overlay.trigger_protection_protocol_demo)
        elif prot_mgr:
            act_prot.triggered.connect(prot_mgr.activate_protocol_demo)
        menu.addAction(act_prot)

    coexist_sub = menu.addMenu("☕ Convivencia && Productividad")
    coexist_sub.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
    coexist_sub.setStyleSheet(menu_stylesheet)

    act_snack = QAction("🍱 Merendar Juntos (Snack / Café Aleatorio)", overlay)
    if hasattr(overlay, "trigger_coexistence_snack"):
        act_snack.triggered.connect(overlay.trigger_coexistence_snack)
    coexist_sub.addAction(act_snack)

    act_dance = QAction("💃 Baile Sincronizado (Coreografía Anime)", overlay)
    if hasattr(overlay, "trigger_choreography_dance"):
        act_dance.triggered.connect(overlay.trigger_choreography_dance)
    coexist_sub.addAction(act_dance)

    act_pomodoro = QAction("🍅 Temporizador Pomodoro de Concentración (25 min)", overlay)
    if hasattr(overlay, "start_pomodoro_session"):
        act_pomodoro.triggered.connect(overlay.start_pomodoro_session)
    coexist_sub.addAction(act_pomodoro)

    act_stretch = QAction("🧘 Pausa Activa y Estiramiento (Regla 20-20-20)", overlay)
    if hasattr(overlay, "trigger_stretch_break"):
        act_stretch.triggered.connect(overlay.trigger_stretch_break)
    coexist_sub.addAction(act_stretch)

    menu.addSeparator()

    act_sync = QAction("🔗 Sincronización de Cuentas (Steam, Spotify, Webhooks)...", overlay)
    act_sync.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
    act_sync.triggered.connect(overlay.open_omni_sync_dialog)
    menu.addAction(act_sync)

    act_settings = QAction("⚙️ Centro de Ajustes && Calibración General...", overlay)
    act_settings.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
    act_settings.triggered.connect(overlay.open_settings_dialog)
    menu.addAction(act_settings)

    model_sub = menu.addMenu("👗 Atuendos && Modelos 3D CyberVR")
    model_sub.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
    model_sub.setStyleSheet(menu_stylesheet)

    canonical_models = [
        ("hoshimachi_suisei", "Hoshimachi Suisei (Maid)", "Atuendo Maid de Gala"),
        ("houshou_marine", "Houshou Marine (V2)", "Capitana Pirata 4K"),
        ("inugami_korone", "Inugami Korone", "Panadera Doog HoloGAMERS"),
        ("nekomata_okayu", "Nekomata Okayu", "Gatita Chill Onigiri"),
        ("tsunomaki_watame", "Tsunomaki Watame", "Ovejita Cantante Afelpada"),
        ("ouro_kronii", "Ouro Kronii", "Guardiana del Tiempo"),
        ("pavolia_reine", "Pavolia Reine", "Princesa Pavo Real"),
        ("hatsune_miku_v4c", "Hatsune Miku V4C", "野餐式 Diva Virtual"),
        ("burnice_white", "Burnice White (ZZZ)", "Sons of Calydon"),
        ("ellen_joe", "Ellen Joe (ZZZ Maid)", "Victoria Housekeeping"),
        ("hoshimi_miyabi", "Hoshimi Miyabi (ZZZ)", "Section 6 Chief"),
        ("jane_doe", "Jane Doe (ZZZ)", "Crim. Investigation"),
        ("anby_demara", "Anby Demara (ZZZ)", "Cunning Hares"),
        ("nicole_demara", "Nicole Demara (ZZZ)", "Cunning Hares Boss")
    ]

    alias_to_canonical = {
        "vanessa": "hoshimachi_suisei",
        "suisei": "hoshimachi_suisei",
        "marine": "houshou_marine",
        "korone": "inugami_korone",
        "okayu": "nekomata_okayu",
        "watame": "tsunomaki_watame",
        "kronii": "ouro_kronii",
        "reine": "pavolia_reine",
        "miku": "hatsune_miku_v4c",
        "burnice": "burnice_white",
        "ellen": "ellen_joe",
        "miyabi": "hoshimi_miyabi",
        "jane": "jane_doe",
        "anby": "anby_demara",
        "nicole": "nicole_demara"
    }

    cur_model = getattr(overlay, "current_vrm_model", "hoshimachi_suisei")
    cur_canonical = alias_to_canonical.get(cur_model, cur_model)

    for m_key, title, desc in canonical_models:
        if m_key not in overlay.vrm_models_map:
            continue
        is_active = (cur_canonical == m_key)
        prefix = "★ " if is_active else "  "
        act_m = QAction(f"{prefix}{title}  ({desc})", overlay)
        if is_active:
            act_m.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        act_m.triggered.connect(lambda ch, k=m_key: overlay.switch_vrm_model(k))
        model_sub.addAction(act_m)

    model_sub.addSeparator()
    act_selector = QAction("🖼️ Catálogo Visual de Atuendos && Modelos...", overlay)
    act_selector.triggered.connect(overlay.open_model_selector_dialog)
    model_sub.addAction(act_selector)

    size_sub = menu.addMenu("📏 Tamaño de Vanessa")
    size_sub.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
    size_sub.setStyleSheet(menu_stylesheet)

    current_preset = getattr(overlay, "current_size_preset", "medium")

    presets = [
        ("small", "Compacto / Pequeño (290 × 480)", 290, 480),
        ("medium", "Intermedio / Equilibrado (350 × 580)  ★ Recomendado", 350, 580),
        ("large", "Grande / Escenario (430 × 710)", 430, 710),
    ]

    for p_key, p_name, pw, ph in presets:
        is_cur = (current_preset == p_key)
        p_prefix = "★ " if is_cur else "  "
        act_p = QAction(f"{p_prefix}{p_name}", overlay)
        if is_cur:
            act_p.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        act_p.triggered.connect(lambda ch, k=p_key, w=pw, h=ph: overlay.set_avatar_size_preset(k, w, h))
        size_sub.addAction(act_p)

    size_sub.addSeparator()
    hint_action = QAction("💡 Ajuste fino: Ctrl + Rueda de ratón", overlay)
    hint_action.setEnabled(False)
    size_sub.addAction(hint_action)

    menu.addSeparator()

    if getattr(overlay, "current_alpha", 1.0) < 0.5:
        act_sleep = QAction("☀️ Despertar a Vanessa", overlay)
        act_sleep.triggered.connect(overlay.wake_up)
    else:
        act_sleep = QAction("🌙 Modo Reposo Discreto", overlay)
        act_sleep.triggered.connect(overlay.enter_sleep_mode)
    menu.addAction(act_sleep)

    act_exit = QAction("❌ Salir del Asistente", overlay)
    act_exit.triggered.connect(overlay.safe_exit)
    menu.addAction(act_exit)

    return menu

def show_context_menu_programmatic(overlay):
    global_pos = overlay.mapToGlobal(QPoint(overlay.width() // 2, overlay.height() // 3))
    dummy_event = QContextMenuEvent(QContextMenuEvent.Reason.Other, QPoint(overlay.width() // 2, overlay.height() // 3), global_pos)
    overlay.contextMenuEvent(dummy_event)
