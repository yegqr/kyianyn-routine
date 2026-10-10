"""Regexes for Telegram posts, copied exactly from docs/PARSING.md: section 2 (classes of a post and Kyiv city,
input of the strike label) and section 7 (preparation signals S1..S5, the word KYIV and the refinements).
Used by silver/telegram_posts.py (table tg_posts) and by the label and signal builders:
    from airalerts.silver.telegram_rx import CLASSES, classify, SIGNALS, KYIV
These patterns are the single source now: change them here, not in PARSING.md. Docs: docs/data/silver/tg_posts.md."""
import re

def K(p): return re.compile(p, re.I)
CLASSES = {
    "missile_threat": K(r"балісти|баллисти|крилат|крылат|ракет|кинджал|кинжал|циркон|іскандер|искандер|калібр|калибр|\bх-?(?:101|22|32|47|55|59|69)\b|ту-?95|ту-?160|ту-?22|міг-?31|миг-?31|kn-?23"),
    "drone_threat": K(r"шахед|шахід|герань|бпла|беспилот|безпілот|дрон|мопед|реактив"),
    "toward_kyiv": K(r"(?:напрям\w*|курс\w*|в бік|в сторону|в направлении|на|повз|через)\s+(?:м\.\s*)?(?:київ(?!щ)|києв(?!о-)|столиц|киев(?!щ))"),
    "explosion": K(r"вибух|взрыв|гучно|громко"),
    "air_defense": K(r"\bппо\b|\bпво\b|збит(?!к)|збив|сбит|сбил|перехоп|\bмінус\b|\bминус\b"),
    "debris": K(r"уламк|обломк"),
    "impact_damage": K(r"влучан|влучил|влучив|попадан|приліт|прильот|прилет|пожеж|пожар|пошкодж|поврежд|руйнув|зруйнов|займан|загоран|постраждал|пострадал|загибл|загинул|погиб|поранен"),
    "all_clear": K(r"відбій|отбой"),
}
KYIV_CITY = K(r"київ(?!щ|ськ)|києв(?!о-)|киев(?!щ|ск)|\bkyiv\b|столиц|голосі|дарниц|деснян|дніпровськ\w* район|оболон|печерськ|подільськ|святошин|солом.ян|шевченківськ\w* район|троєщин|троещин|позняк|осокор|виноградар|борщагів|лук.янів|лівобереж|правобереж|русанівк|теремк")
OBLAST = K(r"київщин|област|обл\.|бровар|борисп|ірпін|ирпен|\bбуч|гостомел|вишгород|обухів|біла церкв|фастів|бояр|вишнев|білогород|васильк|українк|козин|гатн|чабан|гореніч|макарів|бородянк|славутич|іванків|димер|жукин|дмитрівк|баришівк|переяслав|березан|тарасівк|ходосівк|конча|вишеньк|мощун|глевах|хотів|крюківщин|княжич|бортнич|петрівц")
KYIV_ONLY = {"kyiv_airdef", "AerisRimor", "kyiv_nebo", "truexakyiv", "kievreal1", "monitoring_kyiv", "kyivalarm", "VA_Kyiv", "vitaliy_klitschko"}
def classify(channel, text):
    cls = [c for c, rx in CLASSES.items() if rx.search(text)]
    kyiv = bool(KYIV_CITY.search(text)) or (channel in KYIV_ONLY and bool(text) and not OBLAST.search(text))
    return cls, kyiv, kyiv and any(c in cls for c in ("explosion", "debris", "impact_damage"))


# PARSING 7. All patterns compile with re.I; (?-i:...) inside stays case sensitive.
S1 = K(r"\bТу\s*-?\s*(?:95|160|22)|\bTu\s*-?\s*(?:95|160|22)|стратегічн\w*\s+авіац|стратегическ\w*\s+авиац|(?-i:\bСА\b)|Енгельс|Энгельс|Оленья|Оленегорськ|Оленегорск|\b(?:ае|аеродром\w*|аэродром\w*|АБ|авіабаз\w*|авиабаз\w*)\s*«?(?:Українк|Украинк)|Шайковк|Дягілев|Дягилев")
S2 = K(r"М[іи]Г\s*-?\s*31|MiG\s*-?\s*31|Кинджал|Кинжал|Kinzhal|Саваслейк")
S3 = K(r"Калібр|Калибр|Kalibr|ракетоносі|ракетоносц|ракетоносит|носі[їя]в?\s+(?:крилат|Калібр)|носител\w*\s+(?:крылат|Калибр)|КРМБ|морського базування|морского базирования|(?-i:\bФлот\b)")
S4 = K(r"шахед|шахід|Shahed|Герань|Гербер|БпЛА|БПЛА|мопед|🅿|реактив")
S5 = K(r"NOTAM|НОТАМ|закрит\w*\s+(?:неб|повітрян)|закрыт\w*\s+(?:неб|воздушн)|Капустин\w*\s+Яр|Ашулук")
KYIV = K(r"Київ|Киев|Kyiv|Kiev|столиц")
SIGNALS = {"S1": S1, "S2": S2, "S3": S3, "S4": S4, "S5": S5}

# Refinements of PARSING 7: count only together with the main pattern of their signal.
S1_TAKEOFF = K(r"зл[іе]т|взл[её]т|передислок|перебазуван|перекидан|перел[іе]т|перелет")
S1_COUNT = K(r"(\d+)\s*[хx×]?\s*(?:борт|од\.)")
S2_TAKEOFF = K(r"зл[іе]т|взл[её]т|в повітрі|в воздухе|перебуван")
S2_CLEAR = K(r"відбій|отбой")
S3_NONE = K(r"без\s+ракетоносі|без\s+ракетоносц|заведен\w*\s+в\s+порт")
S3_COUNT = K(r"(\d+)\s*[хx×]?\s*(?:надводн\w*\s+|підводн\w*\s+)?(?:ракетоносі|носі[їя]|ракетоносц|носител)")
S4_LAUNCH_PLACE = K(r"пуск\w*[^.\n]{0,80}?\bз\s+(?:полігону|пускового\s+майданчика|аеродрому|району)")
S4_COUNT = K(r"(\d+)\s*[хx×]\s*(?:реактив|Р?БпЛА|шахед|мопед)|🅿️?\s*(\d+)\s*[хx×]")

# The 7 channels PARSING 7 defines the signals for. The patterns do not look at the channel: filter by it.
SIGNAL_CHANNELS = ("war_monitor", "kpszsu", "AerisRimor", "StrategicaviationT", "monitorwarr", "vanek_nikolaev",
                   "kyiv_airdef")


def signals(text):
    """Signals S1..S5 whose main pattern matches the text, in the order S1..S5."""
    return [s for s, rx in SIGNALS.items() if rx.search(text)]
