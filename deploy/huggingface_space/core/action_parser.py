"""
Action parser and dialogue sanitizer for Vanessa 3D VRM and ARKit blendshapes.
Extracts motions and facial expressions specified in dialogue (asterisks, parentheses,
or un-asterisked self-narrating action verbs), maps them to physical gestures,
and completely silences action text from spoken TTS and dialogue balloons.
"""
import re
import random
from typing import Optional, Tuple, List, Dict

MOTION_KEYWORDS = [
    # Japanese Resting Squat (ヤンキー座り / Yankee / Asian resting squat)
    (["descanso japones", "descanso japonés", "yankee", "squat", "sentadilla", "agacha", "agacho", "agacharme", "cuclillas", "en cuclillas"], "japanese_squat"),
    # Maid sit / Sentarse en el borde
    (["sentarse", "sentada", "se sienta", "sienta en el borde", "maid sit", "acomoda su falda", "descanso en borde"], "maid_sit"),
    # Inclinarse curiosa / Curious lean
    (["inclin", "curiosa", "asoma", "lean", "mirar de cerca", "mirar con curiosidad"], "curious_lean"),
    # Acomodar cabello / Shy hair tuck
    (["cabello", "pelo", "tuck", "mechón", "acomoda su pelo", "acomoda su cabello"], "shy_tuck"),
    # Smug arms crossed / Tsundere proud
    (["smug", "brazos cruzados", "orgullosa", "cruza brazos", "presumida"], "smug_cross"),
    # Puchero tsundere / cruzar brazos con berrinche infantil
    (["puchero", "pout", "berrinche", "mejillas infladas"], "pout_arms_crossed"),
    # Asomarse / curiosa / inspección tipo museo
    (["museo", "observa con curiosidad", "mira curiosa", "examin", "inspeccion"], "museum_inspect"),
    # Neko maid / cat pose
    (["neko", "gatita", "gato", "miau", "nyan", "patitas", "zarpas", "cat"], "cat_pose"),
    # Doble paz / otaku peace
    (["doble paz", "doble peace", "dos signos de paz", "otaku peace", "paz kawaii"], "double_peace"),
    # Paz simple
    (["paz", "peace", "signo de la paz", "seña de la paz", "dos dedos"], "peace_wink"),
    # Timidez y sonrojo
    (["timid", "tímid", "sonroja", "deditos", "apenad", "avergonz", "fidget"], "shy_fidget"),
    # Alegría triunfal / puñitos
    (["puñitos", "puño", "fist", "cheer", "victoria", "triunf"], "cheer_fist"),
    # Saludo militar servicial
    (["saludo militar", "salute", "a la orden", "firme"], "salute"),
    # Ofrecer palma / mostrar pantalla
    (["muestra la pantalla", "indica la pantalla", "ofrece la palma", "palma", "offer_palm"], "offer_palm"),
    # Asentir
    (["asiente", "asentir", "nod"], "nod"),
    # Seiza tradicional / sentarse en suelo
    (["seiza", "arrodill", "de rodillas"], "seiza_maid"),
    # Pose tsundere / gacha stand
    (["mano en la cadera", "mano en cadera", "cintura", "tsundere", "pose heroica"], "tsundere_stand"),
    # Apoyarse en ventana / kabe-don
    (["apoy", "pared", "ventana", "kabe-don", "kabedon"], "window_lean"),
    # Reverencia
    (["reverenc", "saludo formal", "respet", "bow"], "bow_polite"),
    # Saludo
    (["salud", "mano", "agita", "hola", "despid", "wave"], "wave_big"),
    # Estiramiento
    (["estira", "estiramiento", "puntitas", "despereza", "stretch"], "stretch_overhead"),
    # Bostezo
    (["bostezo", "sueño", "frotar ojos", "dormir", "yawn"], "yawn"),
    # Corazón
    (["corazon", "corazón", "heart", "cariño"], "heart_hands"),
    # Salto
    (["salt", "brinc", "emocion", "jump"], "victory_jump"),
    # Aplausos
    (["aplaud", "palmada", "aplaus", "celebr", "clap"], "clap_small"),
    # Vuelta / giro
    (["vuelt", "gira", "giro", "vestid", "spin"], "spin"),
    # Pensativa
    (["pens", "reflexion", "medit", "duda", "barbilla", "analiz", "revis", "thinking"], "think_chin"),
    # Encoger hombros
    (["hombro", "encog", "desconoc", "no sabe", "shrug"], "shrug"),
    # Baile
    (["bail", "danz", "ritmo", "dance"], "dance_reze"),
    # Casete walkman
    (["casete", "walkman", "reproductor", "cinta"], "cassette_play"),
    # Alegría / mejillas kawaii
    (["sonr", "alegr", "content", "feliz", "risit", "entusias"], "cheeks_kawaii"),
    # Caminata / paseo
    (["camin", "pase", "andar", "walk", "stroll"], "walk"),
]

EXPRESSION_KEYWORDS = [
    # Exageradas e infantiles anime
    (["pucher", "pout", "berrinche", "mejillas infladas"], "pout"),
    (["gatita", "neko", "cat_face", "miau", "nyan"], "cat_face"),
    (["smug", "presumid", "picar", "pícar", "sonrisa de lado"], "smug"),
    (["shock", "asombr", "susto", "kyaa", "imposible", "ojos abiert"], "shock"),
    (["estrella", "star_eyes", "ojos brillantes", "ilusion", "sii", "emocion infantil"], "star_eyes"),
    (["sonroj", "flustered", "timid", "tímid", "avergonz"], "flustered"),
    (["suplic", "ojitos tiernos", "puppy_eyes", "ojitos tristes"], "puppy_eyes"),
    (["guiñ", "winking", "pestañ", "wink"], "winking_kawaii"),
    # Generales
    (["sonr", "alegr", "feliz", "risa", "risit", "content", "happy"], "happy"),
    (["sorprend", "surpris"], "surprised"),
    (["dulc", "cariñ", "tiern", "afect", "caring"], "caring"),
    (["relaj", "calm", "tranquil", "relax"], "relaxed"),
    (["enojad", "molest", "angry"], "angry"),
    (["trist", "apenad", "sad"], "sad"),
]

# Patterns for self-narrating body actions spoken directly WITHOUT asterisks
# These are extracted into physical motions and completely stripped from spoken speech.
UNASTERISKED_ACTION_PATTERNS = [
    # Agacharse / cuclillas / descanso japonés
    (
        re.compile(r"(?:me\s+voy\s+a\s+agachar|voy\s+a\s+agacharme|me\s+agacho|me\s+pongo\s+de\s+cuclillas|voy\s+a\s+ponerme\s+de\s+cuclillas|me\s+agaché)[^.!?\n]*[.!?]?", re.IGNORECASE),
        "japanese_squat"
    ),
    # Curiosa / inspeccionar / museo / asomarse
    (
        re.compile(r"(?:me\s+asomo|voy\s+a\s+asomarme|me\s+acerco\s+a\s+mirar|voy\s+a\s+observar|me\s+pongo\s+a\s+observar|voy\s+a\s+examinar|me\s+pongo\s+en\s+modo\s+museo)[^.!?\n]*[.!?]?", re.IGNORECASE),
        "museum_inspect"
    ),
    # Sentarse / seiza
    (
        re.compile(r"(?:me\s+siento|voy\s+a\s+sentarme|me\s+acomodo\s+a\s+tu\s+lado|me\s+arrodillo)[^.!?\n]*[.!?]?", re.IGNORECASE),
        "seiza_maid"
    ),
    # Reverencia
    (
        re.compile(r"(?:hago\s+una\s+reverencia|voy\s+a\s+hacer\s+una\s+reverencia|me\s+inclino|me\s+inclino\s+ante\s+ti)[^.!?\n]*[.!?]?", re.IGNORECASE),
        "bow_polite"
    ),
    # Saludar
    (
        re.compile(r"(?:te\s+saludo\s+con\s+la\s+mano|agito\s+mi\s+mano|voy\s+a\s+saludarte)[^.!?\n]*[.!?]?", re.IGNORECASE),
        "wave_big"
    ),
    # Estirarse
    (
        re.compile(r"(?:me\s+estiro\s+en\s+puntitas|me\s+estiro|voy\s+a\s+estirarme)[^.!?\n]*[.!?]?", re.IGNORECASE),
        "stretch_overhead"
    ),
    # Pensar
    (
        re.compile(r"(?:me\s+pongo\s+a\s+pensar|deja\s+que\s+lo\s+piense|pienso\s+un\s+momento)[^.!?\n]*[.!?]?", re.IGNORECASE),
        "think_chin"
    ),
    # Posa / modelar / tsundere
    (
        re.compile(r"(?:poso\s+para\s+ti|voy\s+a\s+posar|hago\s+una\s+pose|pongo\s+las\s+manos\s+en\s+la\s+cadera)[^.!?\n]*[.!?]?", re.IGNORECASE),
        "tsundere_stand"
    ),
    # Neko / gatita
    (
        re.compile(r"(?:hago\s+como\s+gatita|poso\s+como\s+neko|hago\s+miau)[^.!?\n]*[.!?]?", re.IGNORECASE),
        "cat_pose"
    ),
    # Signo de la paz
    (
        re.compile(r"(?:hago\s+el\s+signo\s+de\s+la\s+paz|hago\s+la\s+seña\s+de\s+la\s+paz|te\s+hago\s+el\s+signo\s+de\s+paz)[^.!?\n]*[.!?]?", re.IGNORECASE),
        "peace_wink"
    ),
    # Apoyarse en ventana / kabe-don
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
    """
    Extracts physical actions and expressions from dialogue:
    - Text inside *...* or (...)
    - Direct un-asterisked self-narrating action phrases (e.g. 'me voy a agachar...')
    Maps them to 3D VRM skeletal gestures and ARKit expressions,
    and strips the action text completely so voice and balloons are 100% natural.
    """
    if not text:
        return "", None, None

    found_actions = re.findall(r"\*([^*]+)\*", text)
    parenthesis_actions = re.findall(r"\(([^)]+)\)", text)

    action_texts = found_actions + [
        p for p in parenthesis_actions
        if any(k in p.lower() for k in ["sonr", "reverenc", "inclin", "salud", "salt", "aplaud", "bail", "pens", "pos", "vestid", "agach", "squat", "cuclill", "neko", "paz"])
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

    # Strip asterisks blocks and action parentheses
    clean_text = re.sub(r"\*[^*]*\*", "", text)
    for p in parenthesis_actions:
        if any(k in p.lower() for k in ["sonr", "reverenc", "inclin", "salud", "salt", "aplaud", "bail", "pens", "pos", "vestid", "agach", "squat", "cuclill", "neko", "paz"]):
            clean_text = clean_text.replace(f"({p})", "")

    # Next, detect and strip un-asterisked self-narrating action phrases
    for pattern, motion in UNASTERISKED_ACTION_PATTERNS:
        match = pattern.search(clean_text)
        if match:
            if not detected_motion:
                detected_motion = motion
            # Strip the narrative action phrase
            clean_text = pattern.sub("", clean_text)

    # Clean markdown and formatting artifacts
    clean_text = re.sub(r"[*_#`~]", "", clean_text)
    clean_text = re.sub(r"\s+", " ", clean_text).strip()

    # If dialogue had only action narration, clean_text is empty:
    # User explicitly requested: Do NOT speak the asterisks, execute the physical action,
    # and complement it with a natural, affectionate companion dialogue!
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

    # If no explicit action or expression was tagged in asterisks,
    # infer semantic motion and anime expression directly from spoken meaning!
    if not detected_motion or not detected_expression:
        inf_motion, inf_expr = infer_dialogue_motion_and_expression(clean_text)
        if not detected_motion:
            detected_motion = inf_motion
        if not detected_expression:
            detected_expression = inf_expr

    return clean_text, detected_motion, detected_expression


def infer_dialogue_motion_and_expression(text: str) -> Tuple[str, str]:
    """Infers natural matching 3D VRM motion and exaggerated anime expression from spoken dialogue.
    Prevents senseless or mismatched poses and ensures Vanessa's body acts synchronously with her speech."""
    lower = text.lower()

    # 1. Shock / Asombro / Susto / Impresión
    if any(k in lower for k in ["¡vaya!", "¡cielos!", "¡no puede ser!", "¿de verdad?", "¡kyaa!", "¡dios!", "¡increíble!", "¡imposible!", "¡sorprendente!", "sorprend"]):
        return "surprised_hop", "shock"

    # 2. Pout / Tsundere / Berrinche infantil / Queja cariñosa
    if any(k in lower for k in ["hmpf", "oye", "no soy tu secretaria", "tramposo", "abuso", "no es justo", "bobito", "tontito", "¿acaso crees?", "puchero"]):
        return "pout_arms_crossed", "pout"

    # 3. Neko / Gatita / Kawaii
    if any(k in lower for k in ["miau", "neko", "gatita", "nyan", "patitas", "zarpas"]):
        return "cat_pose", "cat_face"

    # 4. Smug / Presumida / Pícara
    if any(k in lower for k in ["jeje", "para que veas", "obvio", "pan comido", "fácil para mí", "qué esperabas", "te lo dije", "adivina"]):
        return "tsundere_stand", "smug"

    # 5. Star eyes / Éxito / Emoción infantil
    if any(k in lower for k in ["¡lo logramos!", "¡genial!", "¡excelente!", "¡victoria!", "¡vamos!", "¡qué emoción!", "¡fantástico!", "¡maravilloso!", "¡sii!"]):
        return "cheer_fist", "star_eyes"

    # 6. Greetings / Saludos
    if any(k in lower for k in ["hola", "buen día", "buenos días", "buenas tardes", "buenas noches", "bienvenido", "bienvenida", "qué tal"]):
        return "wave_small", "happy"

    # 7. Readiness / Servicial / Órdenes aceptadas
    if any(k in lower for k in ["a la orden", "por supuesto", "enseguida", "de inmediato", "cuenta conmigo", "ahora mismo", "con gusto", "a su servicio"]):
        return "salute", "happy"

    # 8. Showing / Explicando / Mostrando en pantalla
    if any(k in lower for k in ["aquí tienes", "encontré", "puedes ver", "te muestro", "según los datos", "en tu pantalla", "mira esto", "aquí está"]):
        return "offer_palm", "relaxed"

    # 9. Curiosity / Preguntas al Amo
    if any(k in lower for k in ["¿qué", "¿cómo", "¿cuál", "¿por qué", "¿dónde", "¿quién", "me pregunto", "déjame ver", "tengo curiosidad", "curiosa"]):
        return "head_tilt", "surprised"

    # 10. Deep Thinking / Reflexión / Análisis
    if any(k in lower for k in ["pensándolo bien", "déjame pensar", "analizando", "revisando", "consultando", "veamos", "comprobando", "revisar"]):
        return "think_chin", "neutral"

    # 11. Apology / Vergüenza / Timidez
    if any(k in lower for k in ["lo siento", "perdón", "disculpa", "disculpe", "ups", "fue mi error", "qué vergüenza"]):
        return "apology_bow", "flustered"

    # 12. Affection / Amor / Ternura / Cuidados
    if any(k in lower for k in ["con cariño", "te quiero", "cuídate", "a tu lado", "abracito", "descansa", "mi querido amo"]):
        return "heart_hands", "caring"

    # 13. Relief / Suspiro / Cansancio
    if any(k in lower for k in ["¡uf!", "qué alivio", "por fin", "un respiro", "estirarse"]):
        return "sigh_relief", "relaxed"

    # Default conversational: subtle polite nod with pleasant face
    return "nod", "happy"
