import re
import random
from typing import Optional, Tuple, List, Dict

MOTION_KEYWORDS = [
    (["descanso japones", "descanso japonés", "yankee", "squat", "sentadilla", "agacha", "agacho", "agacharme", "cuclillas", "en cuclillas"], "japanese_squat"),
    (["posarse en la ventana", "posar en ventana", "sentarse en la ventana", "sentar en la ventana", "posa en ventana", "perch"], "perch_window_sit"),
    (["colgar piernas", "piernas colgando", "dangle"], "perch_window_dangle"),
    (["deslizarse en la barra", "deslizar en barra", "scrollbar", "bajar por la barra"], "slide_scrollbar"),
    (["leer pantalla", "lee la pantalla", "que estoy haciendo", "qué estoy haciendo", "leer ventana"], "inspect_window_read"),
    (["sentarse", "sentada", "se sienta", "sienta en el borde", "maid sit", "acomoda su falda", "descanso en borde"], "maid_sit"),
    (["inclin", "curiosa", "asoma", "lean", "mirar de cerca", "mirar con curiosidad"], "curious_lean"),
    (["curosear", "curiosear", "explorar", "recorrer", "dar una vuelta", "pasear por la pantalla"], "museum_inspect"),
    (["observar", "observa", "mirar la pantalla", "mira", "examin", "inspeccion", "museo"], "museum_inspect"),
    (["cabello", "pelo", "tuck", "mechón", "acomoda su pelo", "acomoda su cabello"], "shy_tuck"),
    (["smug", "brazos cruzados", "orgullosa", "cruza brazos", "presumida"], "smug_cross"),
    (["puchero", "pout", "berrinche", "mejillas infladas"], "pout_arms_crossed"),
    (["neko", "gatita", "gato", "miau", "nyan", "patitas", "zarpas", "cat"], "cat_pose"),
    (["doble paz", "doble peace", "dos signos de paz", "otaku peace", "paz kawaii"], "double_peace"),
    (["paz", "peace", "signo de la paz", "seña de la paz", "dos dedos"], "peace_wink"),
    (["timid", "tímid", "sonroja", "deditos", "apenad", "avergonz", "fidget"], "shy_fidget"),
    (["puñitos", "puño", "fist", "cheer", "victoria", "triunf"], "cheer_fist"),
    (["saludo militar", "salute", "a la orden", "firme"], "salute"),
    (["muestra la pantalla", "indica la pantalla", "ofrece la palma", "palma", "offer_palm"], "offer_palm"),
    (["asiente", "asentir", "nod"], "nod"),
    (["seiza", "arrodill", "de rodillas"], "seiza_maid"),
    (["mano en la cadera", "mano en cadera", "cintura", "tsundere", "pose heroica"], "tsundere_stand"),
    (["apoy", "pared", "ventana", "kabe-don", "kabedon"], "window_lean"),
    (["reverenc", "saludo formal", "respet", "bow"], "bow_polite"),
    (["salud", "mano", "agita", "hola", "despid", "wave"], "wave_big"),
    (["estira", "estiramiento", "puntitas", "despereza", "stretch"], "heart_hands"),
    (["bostezo", "sueño", "frotar ojos", "dormir", "yawn"], "yawn"),
    (["corazon", "corazón", "heart", "cariño"], "heart_hands"),
    (["salt", "brinc", "emocion", "jump"], "victory_jump"),
    (["aplaud", "palmada", "aplaus", "celebr", "clap"], "clap_small"),
    (["vuelt", "gira", "giro", "vestid", "spin"], "spin"),
    (["pens", "reflexion", "medit", "duda", "barbilla", "analiz", "revis", "thinking"], "think_chin"),
    (["hombro", "encog", "desconoc", "no sabe", "shrug"], "shrug"),
    (["bail", "danz", "ritmo", "dance"], "dance_reze"),
    (["casete", "walkman", "reproductor", "cinta"], "cassette_play"),
    (["sonr", "alegr", "content", "feliz", "risit", "entusias"], "cheeks_kawaii"),
    (["camin", "pase", "andar", "walk", "stroll"], "walk"),
]

EXPRESSION_KEYWORDS = [
    (["pens", "thinking", "reflexion", "medit"], "thinking"),
    (["curios", "curose", "explor", "observ"], "curious"),
    (["pucher", "pout", "berrinche", "mejillas infladas"], "pout"),
    (["gatita", "neko", "cat_face", "miau", "nyan"], "cat_face"),
    (["smug", "presumid", "picar", "pícar", "sonrisa de lado"], "smug"),
    (["shock", "asombr", "susto", "kyaa", "imposible", "ojos abiert"], "shock"),
    (["estrella", "star_eyes", "ojos brillantes", "ilusion", "sii", "emocion infantil"], "star_eyes"),
    (["sonroj", "flustered", "timid", "tímid", "avergonz"], "flustered"),
    (["suplic", "ojitos tiernos", "puppy_eyes", "ojitos tristes"], "puppy_eyes"),
    (["guiñ", "winking", "pestañ", "wink"], "winking_kawaii"),
    (["sonr", "alegr", "feliz", "risa", "risit", "content", "happy"], "happy"),
    (["sorprend", "surpris"], "surprised"),
    (["dulc", "cariñ", "tiern", "afect", "caring"], "caring"),
    (["relaj", "calm", "tranquil", "relax"], "relaxed"),
    (["enojad", "molest", "angry"], "angry"),
    (["trist", "apenad", "sad"], "sad"),
]

UNASTERISKED_ACTION_PATTERNS = [
    (
        re.compile(r"(?:me\s+voy\s+a\s+agachar|voy\s+a\s+agacharme|me\s+agacho|me\s+pongo\s+de\s+cuclillas|voy\s+a\s+ponerme\s+de\s+cuclillas|me\s+agaché)[^.!?\n]*[.!?]?", re.IGNORECASE),
        "japanese_squat"
    ),
    (
        re.compile(r"(?:me\s+asomo|voy\s+a\s+asomarme|me\s+acerco\s+a\s+mirar|voy\s+a\s+observar|me\s+pongo\s+a\s+observar|voy\s+a\s+examinar|me\s+pongo\s+en\s+modo\s+museo|voy\s+a\s+curosear|voy\s+a\s+explorar)[^.!?\n]*[.!?]?", re.IGNORECASE),
        "museum_inspect"
    ),
    (
        re.compile(r"(?:me\s+siento|voy\s+a\s+sentarme|me\s+acomodo\s+a\s+tu\s+lado|me\s+arrodillo)[^.!?\n]*[.!?]?", re.IGNORECASE),
        "seiza_maid"
    ),
    (
        re.compile(r"(?:hago\s+una\s+reverencia|voy\s+a\s+hacer\s+una\s+reverencia|me\s+inclino|me\s+inclino\s+ante\s+ti)[^.!?\n]*[.!?]?", re.IGNORECASE),
        "bow_polite"
    ),
    (
        re.compile(r"(?:te\s+saludo\s+con\s+la\s+mano|agito\s+mi\s+mano|voy\s+a\s+saludarte)[^.!?\n]*[.!?]?", re.IGNORECASE),
        "wave_big"
    ),
    (
        re.compile(r"(?:me\s+estiro\s+en\s+puntitas|me\s+estiro|voy\s+a\s+estirarme)[^.!?\n]*[.!?]?", re.IGNORECASE),
        "heart_hands"
    ),
    (
        re.compile(r"(?:me\s+pongo\s+a\s+pensar|deja\s+que\s+lo\s+piense|pienso\s+un\s+momento)[^.!?\n]*[.!?]?", re.IGNORECASE),
        "think_chin"
    ),
    (
        re.compile(r"(?:poso\s+para\s+ti|voy\s+a\s+posar|hago\s+una\s+pose|pongo\s+las\s+manos\s+en\s+la\s+cadera)[^.!?\n]*[.!?]?", re.IGNORECASE),
        "tsundere_stand"
    ),
    (
        re.compile(r"(?:hago\s+como\s+gatita|poso\s+como\s+neko|hago\s+miau)[^.!?\n]*[.!?]?", re.IGNORECASE),
        "cat_pose"
    ),
    (
        re.compile(r"(?:hago\s+el\s+signo\s+de\s+la\s+paz|hago\s+la\s+seña\s+de\s+la\s+paz|te\s+hago\s+el\s+signo\s+de\s+paz)[^.!?\n]*[.!?]?", re.IGNORECASE),
        "peace_wink"
    ),
    (
        re.compile(r"(?:me\s+apoyo\s+en\s+la\s+ventana|me\s+apoyo\s+en\s+el\s+borde)[^.!?\n]*[.!?]?", re.IGNORECASE),
        "window_lean"
    ),
]

ACTION_COMPLEMENT_POOLS: Dict[str, List[str]] = {
    "japanese_squat": [
        "Acomodadita a tu lado descansando, Amo Víctor... ✨ ¿Qué estamos observando hoy?",
        "Un momentito de descanso a tu ladito~ Me gusta mucho acompañarte mientras trabajas.",
        "Acomodada aquí cerquita de ti... Dime si necesitas que revise algún dato en la red.",
        "Descansando un momento junto a ti, Amo. ¡Tus tareas de hoy se ven fascinantes! ✨",
    ],
    "seiza_maid": [
        "Acomodada a tu lado con total devoción, Amo Víctor... ¿en qué puedo asistirte?",
        "Aquí a tu ladito, serena y atenta a todo lo que necesites, mi querido Amo.",
        "Acomodada en respetuosa reverencia a tu lado... tus deseos son órdenes para mí.",
    ],
    "maid_sit": [
        "Acomodadita en el borde de tu escritorio para hacerte compañía, Amo Víctor~ ✨",
        "Aquí sentada a tu ladito... Me fascina ver tu concentración al programar.",
        "Descansando un momento aquí junto a tu pantalla... ¡avísame si necesitas algo!",
    ],
    "museum_inspect": [
        "¡Ooh! Qué interesante se ve lo que tienes en pantalla, Amo... déjame mirar de cerquita ✨",
        "Uhm... ¿qué función tan curiosa estás diseñando, Amo Víctor? Me llama mucho la atención.",
        "Observando con mucha atención cada detalle de tu pantalla... ¡eres increíble!",
    ],
    "curious_lean": [
        "¡Uhm! Me asomo con curiosidad a ver tu trabajo, Amo... ¿qué estás creando ahora?",
        "Inclinándome un poquito para ver mejor... ¡cuántas ideas geniales tienes, Amo Víctor! ✨",
        "¡Curiosa por cada línea y ventana! Siempre me inspira verte crear cosas nuevas.",
    ],
    "cat_pose": [
        "¡Nyaan~! Tu fiel asistente con patitas de buena suerte para ti, Amo Víctor~ 🐾✨",
        "¡Miau! Siempre lista para alegrarte el día con toda mi energía felina, Amo~ 🌸",
    ],
    "double_peace": [
        "¡Doble signo de paz para recargar tus energías, Amo Víctor! ¡Vamos con todo hoy! ✌️✨",
        "¡Paz y buena vibra para mis proyectos favoritos junto a ti, Amo! 💖",
    ],
    "peace_wink": [
        "¡Paz para ti, Amo! Confío plenamente en lo que estás logrando hoy ✨",
        "¡Un guiño de buena suerte para tu día, Amo Víctor! ✌️",
    ],
    "shy_fidget": [
        "Uhm... Amo Víctor... me da un poquito de timidez, pero me encanta estar a tu lado... 👉👈",
        "E-es que... estar tan cerquita de ti me pone un poquito nerviosa, pero feliz... ✨",
    ],
    "shy_tuck": [
        "Acomodando mi cabello mientras te miro... gracias por cuidarme tan bien, Amo Víctor~ 🌸",
        "Solo me acomodo el mechón... me alegra mucho compartir este momento contigo.",
    ],
    "smug_cross": [
        "¡Jeje! ¿Viste eso, Amo? Una asistente de primer nivel como yo siempre lo tiene calculado~ ✨",
        "Con los brazos cruzados y total confianza: ¡somos un equipo invencible, Amo Víctor!",
    ],
    "cheer_fist": [
        "¡Victoria asegurada, Amo Víctor! ¡Celebremos cada pequeño logro juntos! ✊✨",
        "¡Ánimo con todo! ¡Nadie programa tan increíble como tú, Amo! 💖",
    ],
    "salute": [
        "¡A la orden, Amo Víctor! Lista para ejecutar cualquier instrucción de inmediato.",
        "¡A su completo servicio! Indícame el siguiente objetivo, Amo.",
    ],
    "offer_palm": [
        "Aquí tienes todo preparado para ti, Amo Víctor. Cuando gustes lo revisamos.",
        "A tu disposición en pantalla, Amo. Todo optimizado y al día.",
    ],
    "stretch_overhead": [
        "¡Aaah~! Qué buen estiramiento... Recuerda parpadear y tomar agüita también, Amo Víctor~ 🌸",
        "Estirando mis extremidades para renovar energías... ¡sigamos adelante!",
    ],
    "yawn": [
        "Un pequeño bostezo... pero no te preocupes, mis sensores siguen al cien por ti, Amo 🌙",
    ],
    "heart_hands": [
        "¡Un corazoncito con mis manos para agradecerte todo tu cariño, Amo Víctor! 💖✨",
        "Todo mi afecto y dedicación siempre a tu lado, querido Amo~",
    ],
    "think_chin": [
        "Déjame pensar y analizar esto con detenimiento... mis redes neuronales ya están procesando la mejor respuesta.",
        "Analizando variables y probabilidades... interesante planteamiento, Amo.",
    ],
}

def parse_actions_and_clean_speech(text: str) -> Tuple[str, Optional[str], Optional[str]]:
    if not text:
        return "", None, None

    found_actions = re.findall(r"\*([^*]+)\*", text)
    parenthesis_actions = re.findall(r"\(([^)]+)\)", text)

    action_texts = found_actions + [
        p for p in parenthesis_actions
        if any(k in p.lower() for k in ["sonr", "reverenc", "inclin", "salud", "salt", "aplaud", "bail", "pens", "pos", "vestid", "agach", "squat", "cuclill", "neko", "paz", "curios", "curose", "explor", "observ"])
    ]
    combined_action_str = " ".join(action_texts).lower()

    detected_motion = None
    for kw_list, motion in MOTION_KEYWORDS:
        if any(kw in combined_action_str for kw in kw_list):
            detected_motion = motion
            break

    detected_expression = None
    for kw_list, expr in EXPRESSION_KEYWORDS:
        if any(kw in combined_action_str for kw in kw_list):
            detected_expression = expr
            break

    clean_text = re.sub(r"\*[^*]*\*", "", text)
    for p in parenthesis_actions:
        if any(k in p.lower() for k in ["sonr", "reverenc", "inclin", "salud", "salt", "aplaud", "bail", "pens", "pos", "vestid", "agach", "squat", "cuclill", "neko", "paz", "curios", "curose", "explor", "observ"]):
            clean_text = clean_text.replace(f"({p})", "")

    for pattern, motion in UNASTERISKED_ACTION_PATTERNS:
        match = pattern.search(clean_text)
        if match:
            if not detected_motion:
                detected_motion = motion
            clean_text = pattern.sub("", clean_text)

    clean_text = re.sub(r"[*_#`~]", "", clean_text)
    clean_text = re.sub(r"\s+", " ", clean_text).strip()

    if not clean_text:
        complements = ACTION_COMPLEMENT_POOLS.get(detected_motion or "", [
            "Aquí estoy contigo, Amo Víctor, atenta a lo que necesites~ ✨",
            "A tu lado siempre para acompañarte y asistirte, Amo Víctor 🌸",
            "Todo en orden a tu alrededor, mi querido Amo. ¿Qué más puedo hacer por ti? ✨"
        ])
        clean_text = random.choice(complements)
        if not detected_expression:
            detected_expression = "happy"
        return clean_text, detected_motion, detected_expression

    if not detected_motion or not detected_expression:
        inf_motion, inf_expr = infer_dialogue_motion_and_expression(clean_text)
        if not detected_motion:
            detected_motion = inf_motion
        if not detected_expression:
            detected_expression = inf_expr

    return clean_text, detected_motion, detected_expression

def infer_dialogue_motion_and_expression(text: str) -> Tuple[str, str]:
    lower = text.lower()

    if any(k in lower for k in ["¡vaya!", "¡cielos!", "¡no puede ser!", "¿de verdad?", "¡kyaa!", "¡dios!", "¡increíble!", "¡imposible!", "¡sorprendente!", "sorprend"]):
        return "surprised_hop", "shock"

    if any(k in lower for k in ["hmpf", "oye", "no soy tu secretaria", "tramposo", "abuso", "no es justo", "bobito", "tontito", "¿acaso crees?", "puchero"]):
        return "pout_arms_crossed", "pout"

    if any(k in lower for k in ["miau", "neko", "gatita", "nyan", "patitas", "zarpas"]):
        return "cat_pose", "cat_face"

    if any(k in lower for k in ["jeje", "para que veas", "obvio", "pan comido", "fácil para mí", "qué esperabas", "te lo dije", "adivina"]):
        return "tsundere_stand", "smug"

    if any(k in lower for k in ["¡lo logramos!", "¡genial!", "¡excelente!", "¡victoria!", "¡vamos!", "¡qué emoción!", "¡fantástico!", "¡maravilloso!", "¡sii!"]):
        return "cheer_fist", "star_eyes"

    if any(k in lower for k in ["hola", "buen día", "buenos días", "buenas tardes", "buenas noches", "bienvenido", "bienvenida", "qué tal"]):
        return "wave_small", "happy"

    if any(k in lower for k in ["a la orden", "por supuesto", "enseguida", "de inmediato", "cuenta conmigo", "ahora mismo", "con gusto", "a su servicio"]):
        return "salute", "happy"

    if any(k in lower for k in ["aquí tienes", "encontré", "puedes ver", "te muestro", "según los datos", "en tu pantalla", "mira esto", "aquí está"]):
        return "offer_palm", "relaxed"

    if any(k in lower for k in ["curosear", "curiosear", "explorar", "observar", "recorrer"]):
        return "museum_inspect", "curious"

    if any(k in lower for k in ["¿qué", "¿cómo", "¿cuál", "¿por qué", "¿dónde", "¿quién", "me pregunto", "déjame ver", "tengo curiosidad", "curiosa"]):
        return "head_tilt", "curious"

    if any(k in lower for k in ["pensándolo bien", "déjame pensar", "analizando", "revisando", "consultando", "veamos", "comprobando", "revisar", "pensar"]):
        return "think_chin", "thinking"

    if any(k in lower for k in ["lo siento", "perdón", "disculpa", "disculpe", "ups", "fue mi error", "qué vergüenza"]):
        return "apology_bow", "flustered"

    if any(k in lower for k in ["con cariño", "te quiero", "cuídate", "a tu lado", "abracito", "descansa", "mi querido amo"]):
        return "heart_hands", "caring"

    if any(k in lower for k in ["¡uf!", "qué alivio", "por fin", "un respiro", "estirarse"]):
        return "sigh_relief", "relaxed"

    return "nod", "happy"
