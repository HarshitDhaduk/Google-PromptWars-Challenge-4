"""Demo-mode provider: keyword intents -> real tool calls -> localized templates.

This is deliberately simple and fully deterministic. It exercises the exact
same orchestrator and tool layer as Gemini - only the "brain" is swapped -
so judges without an API key still see grounded routes, amenity search, and
crowd-aware advice. Template quality covers en/es/fr; other locales fall back
to English (full language breadth is Gemini's job).
"""

import re
from dataclasses import dataclass
from typing import Sequence

from .provider import (
    FunctionCallTurn,
    HistoryTurn,
    TextTurn,
    ToolCall,
    ToolDeclaration,
    ToolExchange,
    Turn,
)

TEMPLATE_LANGS = ("en", "es", "fr")

_ARABIC_CHARS = re.compile(r"[؀-ۿ]")

_WORD_MARKERS: dict[str, frozenset[str]] = {
    "es": frozenset(
        "dónde donde baño baños asiento comida salir cuándo cuando cerca "
        "ayuda puedo necesito estadio lleno gol marcador tren".split()
    ),
    "fr": frozenset(
        "où toilettes siège sortir quand proche aide manger trouver peux "
        "où est stade foule but".split()
    ),
    "pt": frozenset(
        "onde banheiro assento sair obrigado você preciso perto lotado placar".split()
    ),
    "de": frozenset(
        "wo toilette toiletten sitzplatz essen wann hilfe ausgang finde "
        "wie komme voll spielstand".split()
    ),
}


def detect_language(message: str, fallback: str) -> str:
    """Best-effort language sniff so demo mode answers Spanish in Spanish."""
    if _ARABIC_CHARS.search(message):
        return "ar"
    if "¿" in message or "¡" in message:
        return "es"
    words = frozenset(re.findall(r"[a-zà-öø-ÿœ]+", message.casefold()))
    scores = {lang: len(words & markers) for lang, markers in _WORD_MARKERS.items()}
    best = max(sorted(scores), key=lambda lang: scores[lang])
    if scores[best] > 0:
        return best
    return fallback


def _reply_language(message: str, locale: str) -> str:
    detected = detect_language(message, locale)
    if detected in TEMPLATE_LANGS:
        return detected
    if locale in TEMPLATE_LANGS:
        return locale
    return "en"


# ---------------------------------------------------------------------------
# Intent detection
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Intent:
    name: str
    keywords: tuple[str, ...]
    call: ToolCall


def _kw(*words: str) -> tuple[str, ...]:
    return words


_DIETARY_KEYWORDS = {
    "halal": _kw("halal", "حلال"),
    "vegan": _kw("vegan", "vegano", "vegana", "végétalien", "vegane"),
    "vegetarian": _kw(
        "vegetarian", "vegetariano", "vegetariana", "végétarien", "végétarienne",
        "vegetarisch", "نباتي",
    ),
    "gluten_free": _kw("gluten", "glutenfrei", "glúten"),
}

_INTENTS: tuple[_Intent, ...] = (
    _Intent(
        "first_aid",
        _kw(
            "first aid", "medic", "medical", "hurt", "injured", "unwell", "dizzy",
            "primeros auxilios", "enfermería", "enfermeria", "médico", "medico", "herido",
            "premiers secours", "infirmerie", "blessé", "blesse",
            "erste hilfe", "arzt", "verletzt",
            "primeiros socorros", "machucado",
            "إسعاف", "طبيب", "مصاب",
        ),
        ToolCall("find_amenities", {"category": "first_aid"}),
    ),
    _Intent(
        "accessible_route",
        _kw(
            "accessible", "wheelchair", "step-free", "step free", "no stairs",
            "elevator", "lift", "mobility",
            "accesible", "silla de ruedas", "sin escaleras", "ascensor",
            "fauteuil roulant", "sans escaliers", "ascenseur",
            "barrierefrei", "rollstuhl", "aufzug", "ohne treppen",
            "acessível", "acessivel", "cadeira de rodas", "sem escadas", "elevador",
            "كرسي متحرك", "بدون درج", "مصعد",
        ),
        ToolCall("get_route", {"to": "my_seat", "accessible": True}),
    ),
    _Intent(
        "transit",
        _kw(
            "leave", "exit", "train", "bus", "transit", "go home", "get out",
            "depart", "beat the rush",
            "salir", "salida", "tren", "autobús", "autobus", "irme",
            "partir", "sortir", "sortie",
            "verlassen", "zug", "ausgang", "abfahren",
            "sair", "saída", "saida", "trem", "ônibus", "onibus",
            "مغادرة", "أغادر", "قطار", "خروج", "حافلة",
        ),
        ToolCall("get_transit_advice", {}),
    ),
    _Intent(
        "prayer",
        _kw(
            "prayer", "pray", "mosque", "chapel", "worship",
            "oración", "oracion", "rezar", "orar",
            "prière", "priere", "prier",
            "gebet", "beten",
            "oração", "oracao",
            "صلاة", "مصلى", "أصلي",
        ),
        ToolCall("find_amenities", {"category": "prayer"}),
    ),
    _Intent(
        "sensory",
        _kw(
            "sensory", "quiet room", "autism", "overwhelmed", "sensorial",
            "sensoriel", "sensorielle", "ruheraum", "غرفة هادئة",
        ),
        ToolCall("find_amenities", {"category": "sensory_room"}),
    ),
    _Intent(
        "restroom",
        _kw(
            "restroom", "toilet", "bathroom", "washroom", "loo",
            "baño", "baños", "aseo", "servicios",
            "toilettes", "wc",
            "toilette", "toiletten", "klo",
            "banheiro",
            "حمام", "مرحاض", "دورة مياه",
        ),
        ToolCall("find_amenities", {"category": "restroom"}),
    ),
    _Intent(
        "water",
        _kw(
            "water", "refill", "agua", "eau", "wasser", "água", "ماء", "مياه",
        ),
        ToolCall("find_amenities", {"category": "water"}),
    ),
    _Intent(
        "food",
        _kw(
            "food", "eat", "hungry", "restaurant", "snack", "pizza", "burger",
            "halal", "vegan", "vegetarian", "gluten",
            "comida", "comer", "hambre", "restaurante", "vegano", "vegetariana", "vegetariano",
            "manger", "nourriture", "faim", "végétarien", "végétalien",
            "essen", "hungrig", "vegetarisch", "glutenfrei",
            "fome", "lanche", "glúten",
            "طعام", "آكل", "جائع", "حلال", "نباتي",
        ),
        ToolCall("find_amenities", {"category": "food"}),
    ),
    _Intent(
        "merch",
        _kw(
            "store", "shop", "merch", "jersey", "souvenir",
            "tienda", "camiseta", "recuerdo",
            "boutique", "maillot",
            "fanshop", "trikot",
            "loja", "camisa", "lembrança", "lembranca",
            "متجر", "قميص",
        ),
        ToolCall("find_amenities", {"category": "merch"}),
    ),
    _Intent(
        "crowd",
        _kw(
            "crowd", "crowded", "busy", "congestion", "packed", "queue", "line",
            "multitud", "lleno", "gente", "cola", "fila",
            "foule", "monde", "bondé", "bonde", "file",
            "voll", "menge", "schlange", "überfüllt",
            "lotado", "multidão", "multidao", "cheio",
            "ازدحام", "زحمة", "مزدحم",
        ),
        ToolCall("get_crowd_status", {}),
    ),
    _Intent(
        "match",
        _kw(
            "score", "goal", "match", "game", "result", "winning", "kickoff",
            "marcador", "gol", "partido", "resultado",
            "but", "résultat", "resultat",
            "spielstand", "ergebnis", "spiel",
            "placar", "jogo",
            "نتيجة", "هدف", "مباراة",
        ),
        ToolCall("get_match_info", {}),
    ),
    _Intent(
        "seats_available",
        _kw(
            "seats", "seat availability", "available seats", "any seats", "upgrade",
            "resale", "extra tickets", "buy tickets",
            "asientos", "hay asientos", "entradas disponibles",
            "places disponibles", "billets disponibles",
            "sitze", "freie plätze", "karten verfügbar",
            "assentos", "ingressos disponíveis",
            "مقاعد", "تذاكر متاحة",
        ),
        ToolCall("find_available_seats", {}),
    ),
    _Intent(
        "seat_route",
        _kw(
            "seat", "my section", "find my", "section", "block",
            "asiento", "mi sección", "mi seccion", "sección",
            "siège", "siege", "ma place",
            "sitzplatz", "sitz", "platz",
            "assento", "meu lugar", "seção", "secao",
            "مقعد", "مقعدي", "القسم",
        ),
        ToolCall("get_route", {"to": "my_seat"}),
    ),
    _Intent(
        "ticket",
        _kw(
            "ticket", "which gate", "my gate", "entrance",
            "boleto", "entrada", "puerta",
            "billet", "porte", "entrée", "entree",
            "eingang",
            "ingresso", "bilhete", "portão", "portao",
            "تذكرة", "بوابة",
        ),
        ToolCall("get_ticket_context", {}),
    ),
)


def _detect_intent(message: str) -> _Intent | None:
    lowered = message.casefold()
    for intent in _INTENTS:
        for keyword in intent.keywords:
            if re.search(rf"(?<!\w){re.escape(keyword)}(?!\w)", lowered):
                return intent
    return None


def _dietary_filter(message: str) -> str | None:
    lowered = message.casefold()
    for tag, keywords in _DIETARY_KEYWORDS.items():
        for keyword in keywords:
            if re.search(rf"(?<!\w){re.escape(keyword)}(?!\w)", lowered):
                return tag
    return None


# ---------------------------------------------------------------------------
# Localized rendering from real tool results
# ---------------------------------------------------------------------------

_CROWD_WORDS = {
    "en": {"low": "calm", "moderate": "moderately busy", "high": "busy", "severe": "extremely busy"},
    "es": {"low": "tranquilo", "moderate": "algo concurrido", "high": "concurrido", "severe": "saturado"},
    "fr": {"low": "calme", "moderate": "assez fréquenté", "high": "très fréquenté", "severe": "bondé"},
}

_TRANSIT_ADVICE = {
    "en": {
        "pre_match": "No exit planning needed yet - enjoy the build-up.",
        "enjoy": "Relax and enjoy the match; ask me again around the 75th minute.",
        "leave_early": "To beat the rush, leave about 10 minutes before the final whistle.",
        "wait_out": "Waiting 20-30 minutes on the concourse (or the bus queue) is usually faster than joining the crush.",
        "go_now": "Crowds have eased - a good moment to head out.",
    },
    "es": {
        "pre_match": "Aún no necesitas planear tu salida: disfruta la previa.",
        "enjoy": "Disfruta el partido; pregúntame de nuevo hacia el minuto 75.",
        "leave_early": "Para evitar la multitud, sal unos 10 minutos antes del final.",
        "wait_out": "Esperar 20-30 minutos en el concourse (o la fila del autobús) suele ser más rápido que unirse a la marea.",
        "go_now": "Las multitudes han bajado: buen momento para salir.",
    },
    "fr": {
        "pre_match": "Pas besoin de planifier votre sortie pour l'instant - profitez de l'avant-match.",
        "enjoy": "Profitez du match ; redemandez-moi vers la 75e minute.",
        "leave_early": "Pour éviter la cohue, partez environ 10 minutes avant le coup de sifflet final.",
        "wait_out": "Attendre 20-30 minutes dans le concourse (ou la file du bus) est souvent plus rapide que la cohue.",
        "go_now": "La foule s'est dissipée - bon moment pour partir.",
    },
}

_STRINGS = {
    "en": {
        "route": "Your route to {to} takes about {minutes} min from {from_}:\n{steps}",
        "route_map": "The route is highlighted on the map.",
        "seat_suffix": "Your seat: {seat}.",
        "amenities": "Closest options from {from_}:\n{items}\nThey are highlighted on the map.",
        "amenity_line": "{index}. {name} - {zone} (~{eta} min)",
        "amenities_empty": "I could not find anything matching that. Guest Services at Gate A or C can help.",
        "crowd_summary": "Right now ({phase}): busiest - {busiest}. Calmest - {calmest}.",
        "crowd_zone": "{zone} is {word} right now (walk times about {multiplier}x normal).",
        "transit": "From {from_}, the rail and bus plaza is a {eta} min walk and currently {word}. {advice}",
        "match_pre": "{fixture} kicks off in {minutes} minutes at {venue}. Gates are open - enjoy!",
        "match_live": "{score} ({minute}'). {events}",
        "match_post": "Full time: {score}. {events}",
        "goals": "Goals: {list}.",
        "no_goals": "No goals yet.",
        "ticket": "You are in Section {section}, Row {row}, Seat {seat} - enter via Gate {gate}. You are currently near {current}.",
        "seats_list": "Sections with seats still available:\n{items}\nThe stand with the most availability is highlighted on the map.",
        "seats_line": "{index}. Section {section} - {zone} ({available} seats)",
        "seats_empty": "Right now every section is sold out. Official resale may release returns - check Guest Services at Gate A or C.",
        "error": "I could not find that. Try a section number like '324', an amenity, or 'my seat'. Guest Services at Gate A or C can also help.",
        "capabilities": (
            "I can guide you around MetLife Stadium: find your seat, the nearest food "
            "(halal, vegan, gluten-free...), restrooms, water, first aid or the prayer room, "
            "check crowd levels and the score, and time your exit. Try 'Take me to my seat' "
            "or 'Nearest halal food'."
        ),
    },
    "es": {
        "route": "Tu ruta hacia {to} toma unos {minutes} min desde {from_}. Sigue los pasos numerados en la tarjeta de ruta.",
        "route_map": "La ruta está resaltada en el mapa.",
        "seat_suffix": "Tu asiento: {seat}.",
        "amenities": "Opciones más cercanas desde {from_}:\n{items}\nEstán resaltadas en el mapa.",
        "amenity_line": "{index}. {name} - {zone} (~{eta} min)",
        "amenities_empty": "No encontré nada con esos filtros. Atención al Cliente en la Puerta A o C puede ayudarte.",
        "crowd_summary": "Ahora mismo ({phase}): más concurrido - {busiest}. Más tranquilo - {calmest}.",
        "crowd_zone": "{zone} está {word} ahora (tiempos de caminata ~{multiplier}x).",
        "transit": "Desde {from_}, la plaza de tren y autobús está a {eta} min a pie y ahora está {word}. {advice}",
        "match_pre": "{fixture} comienza en {minutes} minutos en {venue}. ¡Las puertas están abiertas!",
        "match_live": "{score} ({minute}'). {events}",
        "match_post": "Final del partido: {score}. {events}",
        "goals": "Goles: {list}.",
        "no_goals": "Aún no hay goles.",
        "ticket": "Estás en la Sección {section}, Fila {row}, Asiento {seat}; entra por la Puerta {gate}. Ahora estás cerca de {current}.",
        "seats_list": "Secciones con asientos disponibles:\n{items}\nLa zona con más disponibilidad está resaltada en el mapa.",
        "seats_line": "{index}. Sección {section} - {zone} ({available} asientos)",
        "seats_empty": "Ahora mismo todo está agotado. La reventa oficial puede liberar entradas: consulta Atención al Cliente en la Puerta A o C.",
        "error": "No pude encontrar eso. Prueba con un número de sección como '324', un servicio, o 'mi asiento'.",
        "capabilities": (
            "Puedo guiarte por el MetLife Stadium: encontrar tu asiento, la comida más cercana "
            "(halal, vegana, sin gluten...), baños, agua, primeros auxilios o la sala de oración, "
            "ver el nivel de gente y el marcador, y elegir el mejor momento para salir. "
            "Prueba 'Llévame a mi asiento' o 'Comida halal cerca'."
        ),
    },
    "fr": {
        "route": "Votre trajet vers {to} prend environ {minutes} min depuis {from_}. Suivez les étapes numérotées sur la carte d'itinéraire.",
        "route_map": "L'itinéraire est surligné sur le plan.",
        "seat_suffix": "Votre place : {seat}.",
        "amenities": "Options les plus proches depuis {from_} :\n{items}\nElles sont surlignées sur le plan.",
        "amenity_line": "{index}. {name} - {zone} (~{eta} min)",
        "amenities_empty": "Je n'ai rien trouvé avec ces critères. Les services aux spectateurs (Porte A ou C) peuvent aider.",
        "crowd_summary": "En ce moment ({phase}) : le plus fréquenté - {busiest}. Le plus calme - {calmest}.",
        "crowd_zone": "{zone} est {word} en ce moment (temps de marche ~{multiplier}x).",
        "transit": "Depuis {from_}, l'esplanade rail et bus est à {eta} min à pied, actuellement {word}. {advice}",
        "match_pre": "{fixture} commence dans {minutes} minutes au {venue}. Les portes sont ouvertes !",
        "match_live": "{score} ({minute}'). {events}",
        "match_post": "Fin du match : {score}. {events}",
        "goals": "Buts : {list}.",
        "no_goals": "Pas encore de but.",
        "ticket": "Vous êtes en Section {section}, Rang {row}, Place {seat} ; entrez par la Porte {gate}. Vous êtes actuellement près de {current}.",
        "seats_list": "Sections avec des places encore disponibles :\n{items}\nLa tribune avec le plus de places est surlignée sur le plan.",
        "seats_line": "{index}. Section {section} - {zone} ({available} places)",
        "seats_empty": "Tout est complet pour le moment. La revente officielle peut libérer des places - voyez les services aux spectateurs (Porte A ou C).",
        "error": "Je n'ai pas trouvé. Essayez un numéro de section comme '324', un service, ou 'ma place'.",
        "capabilities": (
            "Je peux vous guider dans le MetLife Stadium : trouver votre place, la nourriture la plus "
            "proche (halal, végétalien, sans gluten...), les toilettes, l'eau, les premiers secours ou "
            "la salle de prière, vérifier l'affluence et le score, et choisir le bon moment pour partir. "
            "Essayez « Emmène-moi à ma place »."
        ),
    },
}


def _zone_list(entries: Sequence[dict], lang: str) -> str:
    words = _CROWD_WORDS[lang]
    return ", ".join(f"{entry['zone_name']} ({words[entry['crowd_label']]})" for entry in entries)


def _render(call: ToolCall, data: dict, lang: str) -> str:
    strings = _STRINGS[lang]
    if "error" in data:
        return strings["error"]

    if call.name == "get_route":
        parts = [
            strings["route"].format(
                to=data["to"],
                from_=data["from"],
                minutes=data["total_minutes"],
                steps="\n".join(
                    f"{index}. {step}" for index, step in enumerate(data["steps"], start=1)
                ),
            )
        ]
        if "at_destination" in data:
            parts.append(strings["seat_suffix"].format(seat=data["at_destination"]))
        parts.append(strings["route_map"])
        return " ".join(parts) if lang != "en" else "\n".join(parts)

    if call.name == "find_amenities":
        results = data.get("results", [])
        if not results:
            return strings["amenities_empty"]
        items = "\n".join(
            strings["amenity_line"].format(
                index=index, name=item["name"], zone=item["zone_name"], eta=item["eta_minutes"]
            )
            for index, item in enumerate(results, start=1)
        )
        return strings["amenities"].format(from_=data["from_name"], items=items)

    if call.name == "get_crowd_status":
        if "zone_name" in data:
            return strings["crowd_zone"].format(
                zone=data["zone_name"],
                word=_CROWD_WORDS[lang][data["crowd_label"]],
                multiplier=data["walk_time_multiplier"],
            )
        return strings["crowd_summary"].format(
            phase=data["phase"].replace("_", " "),
            busiest=_zone_list(data["busiest"][:3], lang),
            calmest=_zone_list(data["calmest"][:2], lang),
        )

    if call.name == "get_transit_advice":
        rail = data["options"][0]
        return strings["transit"].format(
            from_=data["from"],
            eta=rail["walk_eta_minutes"],
            word=_CROWD_WORDS[lang][data["rail_plaza_crowd"]],
            advice=_TRANSIT_ADVICE[lang][data["advice_key"]],
        )

    if call.name == "get_match_info":
        events = data.get("events_so_far", [])
        if events:
            goal_list = ", ".join(f"{event['player']} {event['minute']}'" for event in events)
            events_text = strings["goals"].format(list=goal_list)
        else:
            events_text = strings["no_goals"]
        if data.get("minutes_to_kickoff") is not None:
            return strings["match_pre"].format(
                fixture=data["fixture"],
                minutes=data["minutes_to_kickoff"],
                venue=data["venue"],
            )
        key = "match_post" if data["phase"] == "post_match" else "match_live"
        return strings[key].format(
            score=data["score"], minute=data.get("match_minute"), events=events_text
        )

    if call.name == "get_ticket_context":
        return strings["ticket"].format(
            section=data["section"],
            row=data["row"],
            seat=data["seat"],
            gate=data["entry_gate"],
            current=data["current_location_name"],
        )

    if call.name == "find_available_seats":
        sections = data.get("sections", [])
        if not sections:
            return strings["seats_empty"]
        items = "\n".join(
            strings["seats_line"].format(
                index=index,
                section=item["section"],
                zone=item["zone_name"],
                available=item["available"],
            )
            for index, item in enumerate(sections, start=1)
        )
        return strings["seats_list"].format(items=items)

    return strings["capabilities"]


class MockProvider:
    """Deterministic stand-in for Gemini used in demo mode and as fallback."""

    name = "mock"

    def generate_turn(
        self,
        *,
        system: str,
        history: Sequence[HistoryTurn],
        message: str,
        locale: str,
        exchanges: Sequence[ToolExchange],
        declarations: Sequence[ToolDeclaration],
    ) -> Turn:
        lang = _reply_language(message, locale)

        if not exchanges:
            intent = _detect_intent(message)
            if intent is None:
                return TextTurn(text=_STRINGS[lang]["capabilities"])
            call = intent.call
            if call.name == "find_amenities" and call.args.get("category") == "food":
                dietary = _dietary_filter(message)
                if dietary is not None:
                    call = ToolCall(call.name, {**call.args, "dietary": dietary})
            if call.name == "get_route":
                section = re.search(r"\b(\d{3})\b", message)
                if section:
                    call = ToolCall(call.name, {**call.args, "to": section.group(1)})
            return FunctionCallTurn(calls=[call])

        exchange = exchanges[-1]
        if not exchange.results:
            return TextTurn(text=_STRINGS[lang]["error"])
        result = exchange.results[0]
        return TextTurn(text=_render(result.call, result.data, lang))
