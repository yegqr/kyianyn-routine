"""Export this project's Claude Code conversations to chats/ with every key and private detail cut (chats/README.md).

The KSE form asks for the full text export of the conversations with the AI tool. Every Claude Code session of the
project (one <session>.jsonl in --src; the session folders hold subagent transcripts and stay out) becomes one Markdown
file, chats/NN-YYYY-MM-DD-<slug>.md, numbered by its first timestamp; all-chats.md holds a contents table and then every
session in order; README.md says how to read them. Hidden thinking, system reminders and service entries are skipped,
tool inputs and outputs are trimmed. A skill body, a read of SKILL.md, AGENTS.md or CLAUDE.md, any read of the author's
rules and skills (~/.claude outside projects, ~/.agent) and the output of a command that reads what subagents wrote (a
workflow journal.jsonl, a session's subagents folder, a workflow's task output) become one italic line; the output of a
command that lists the server's services, sites, jobs, ports or processes (ps too) becomes one mark. One method,
Redactor.redact(), runs over every piece of text before it is trimmed and written: keys and tokens, any value after a
key name (in quotes, backticks, brackets or bold too; a bracketed value whole), high-entropy strings, IP addresses (dots
escaped in a regex too), e-mails, phones, a path into a dot-folder of the home directory (but ~/.claude/projects,
~/.cache and ~/.npm; written without ~/ too, as .claude/skills, for every dot-folder the sessions show in a home
directory) and the private words from --deny (a list kept outside the repo on purpose; a word also matches with - _ . /
or a space between its parts, or none, as in camelCase, and takes the dotted name around it) become a visible
[REDACTED: ...] mark. In any text (a message, a reply, a tool input or output, a context summary, a title) a
line with a vault command, the PIN or a detail of how the server and the keys are guarded (the regular expressions on
the lines of --deny that start with !, kept outside the repo like the private words) is cut whole, so is a line that
names two or more of the server's other sites (the lines of --deny that start with ~) or one of them next to True or
False, and so is a row of the privacy review's findings (a
chat file, a line and a kind). In tool text a line with a private word or server_name is cut whole too, and in a tool
result so is a line with a systemd service or timer of another project. A last pass cuts any later fragment of a value
already cut, such as a key split by a line break. The rules are strict on purpose: a line of code that only looks like
a key is cut too, except plain code values after key, keys or sort_keys and the Co-Authored-By line; a path made of
words stays, a random piece in it is cut; every high-entropy cut is listed in --review. A session missing from TOPICS
is named by its redacted ai-title. Nothing printed or written to --review shows more than the first 3 characters of a
cut value. Re-running rewrites the output folder completely, so a running session can grow.

    .venv/bin/python -I scripts/chats/export.py --deny <private word list> [--review <file>] [--src DIR] [--out DIR]
"""
import argparse
import json
import math
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
SRC = Path.home() / ".claude" / "projects" / "-home-ye-PROJECTS-ai-school-airalers"
OUT = ROOT / "chats"
KYIV = ZoneInfo("Europe/Kyiv")
TOPICS = {  # session id start: (topic, file slug); a session not listed here takes its last ai-title
    "871ac248": ("Завдання і план даних", "assignment-and-data-plan"),
    "1ff910c8": ("Збір даних: bronze, silver, gold", "data-collection-bronze-silver-gold"),
    "e1021ac6": ("Прибирання і перевірка сигналу", "cleanup-and-signal-check"),
    "ad9ddb95": ("Аудит даних перед моделюванням", "data-audit-before-modelling"),
    "300bed96": ("Моделювання", "modelling"),
    "304146ba": ("Живий сайт і презентація", "live-site-and-deck"),
    "aa6a06fb": ("Фінальне шліфування і публікація", "final-polish-and-publish"),
}
KEY, ENT, FRAG, IP, MAIL, PHONE = "ключ", "ентропія", "уламок", "IP", "e-mail", "телефон"
PRIV, SERVER = "приватне", "сервер"  # a private word; a listing of the server's services and sites or a line from one
PATH, SAFE = "шлях", "захист"  # a path into a private dot-folder of the home directory; a line on how keys and server are guarded
REVIEW = "огляд"  # a row of the privacy review's findings: it retells what is cut elsewhere
KINDS = (KEY, ENT, FRAG, IP, MAIL, PHONE, PRIV, SERVER, PATH, SAFE, REVIEW)
MARK = {KEY: "[REDACTED: ключ]", FRAG: "[REDACTED: ключ]", IP: "[REDACTED: IP]", MAIL: "[REDACTED: e-mail]",
        PHONE: "[REDACTED: телефон]", PRIV: "[REDACTED]", PATH: "[REDACTED: приватний шлях]"}
LINE_MARK = "[REDACTED: рядок про інші приватні проєкти]"
SERVER_MARK = "[REDACTED: перелік служб і сайтів сервера]"
SAFE_MARK = "[REDACTED: рядок про захист сервера і ключів]"
REVIEW_MARK = "[REDACTED: рядок з огляду приватності]"
INSTRUCTION_FILES = ("SKILL.md", "AGENTS.md", "CLAUDE.md")
ALLOWED_MAILS = {"yisakov@kse.org.ua", "noreply@anthropic.com"}
ALLOWED_IPS = {"127.0.0.1", "0.0.0.0"}
SEP = r"[-_./ ]{0,2}"  # between the parts of a private word: - _ . / or a space, or nothing (camelCase)

KEYS = [re.compile(p) for p in (  # the whole match is a key
    r"-----BEGIN[A-Z ]*PRIVATE KEY-----[\s\S]*?(?:-----END[A-Z ]*PRIVATE KEY-----|\Z)",
    r"(?i)apik[\w.\-]*", r"sk-ant[\w\-]*", r"(?<![\w\-])sk-[A-Za-z0-9_\-]{16,}",
    r"gh[po]_[A-Za-z0-9_]*", r"(?<![A-Za-z0-9])gh[usr]_[A-Za-z0-9_]{8,}", r"github_pat_[A-Za-z0-9_]*",
    r"AKIA[0-9A-Z]{12,}", r"xox[abposr]-[A-Za-z0-9\-]{8,}", r"(?<!\d)\d{6,12}:[A-Za-z0-9_\-]{30,}",
    r"AIza[0-9A-Za-z_\-]{20,}", r"ya29\.[0-9A-Za-z_\-]{10,}", r"eyJ[A-Za-z0-9_\-]{10,}(?:\.[A-Za-z0-9_\-]{4,}){0,2}",
)]
KEEP = [re.compile(p) for p in (  # group 1 stays, group 2 is the key
    r"(?i)(\bBearer\s+)([A-Za-z0-9._~+/=\-]{6,})",
    r"(\b(?:Basic|Digest) +)((?=[A-Za-z0-9+/]*[0-9+/=])[A-Za-z0-9+/=]{8,})",
    r"(?i)(\b[a-z][a-z0-9+.\-]*://)([^\s/:@]+:[^\s/@]+)(?=@)",
)]
NAMES = r"(?:key|token|secret|passw(?:or)?d|pwd|auth|cookie|session|api_?hash)"
NAME = rf"(?<![\w.\-])[\w.\-]*{NAMES}[\w.\-]*"
CLOSE = r"[\"'`\])*]{0,4}"  # the name in quotes, backticks, brackets or bold: "key", `MAX_TOKENS`, got[key], **Token**
# any value: quoted, in backticks, a <placeholder> or bare, code such as key=lambda too
VALUE = r"(\"[^\"\n]+\"|'[^'\n]+'|`[^`\n]+`|<[^<>\n]+>|[^\s\"'`,;()\[\]{}<>*|&]+)"
NAMED = [re.compile(rf"(?i)({NAME}{CLOSE}{gap}[=:]{{1,2}}{gap}\**{gap})(?![=:]){VALUE}")  # **Password:** value too
         for gap in (r"[ \t]*", r"\s*")]  # a value on the same line first, then one on the next line
FLAG = re.compile(rf"(?i)((?<![\w\-])--?[\w\-]*{NAMES}[\w\-]*\s+)(?!-){VALUE}")
DANGLING = re.compile(rf"(?i){NAME}{CLOSE}\s*[=:]{{1,2}}\s*\**\s*\Z")  # its value is past the cut
OPEN = re.compile(rf"(?i)({NAME}{CLOSE}\s*[=:]{{1,2}}\s*\**\s*)[(\[{{]")  # a bracketed value
KEEP_NAMES = {"key", "keys", "sort_keys"}  # plain code values after these stay: sorted(rows, key=len), sort_keys=True
IDENT = r"_*[A-Za-z]{1,20}[0-9]{0,3}(?:[._]+[A-Za-z]{1,20}[0-9]{0,3})*_*"  # a name made of words, not a random string
CODE = re.compile(rf"(?i:true|false|none|null)|-?[0-9]{{1,8}}(?:\.[0-9]+)?|lambda\b.*|{IDENT}")
ITEM = rf"\s*(?:{IDENT}|\"[A-Za-z0-9_ .\-]{{0,24}}\"|'[A-Za-z0-9_ .\-]{{0,24}}')\s*"
ITEMS = re.compile(rf"\((?:{ITEM}(?:,{ITEM})*,?\s*)?\)|\[(?:{ITEM}(?:,{ITEM})*,?\s*)?\]")  # a tuple or list of names
UNIT = re.compile(r"(?<![\w@.\-])([\w@.\-]+)\.(?:service|timer)\b")
OWN_UNIT = re.compile(r"(?:kyianyn-routine|livii-bereh)[\w@.\-]*|systemd-[\w@.\-]+|sshd?|nginx|cron|dbus|networkd[\w.\-]*|resolved"
                      r"|journald|timesyncd|snapd[\w.\-]*|ufw|fail2ban|unattended-upgrades|user@[\w.\-]*")  # ours or stock
INVENTORY = re.compile(  # a shell command whose output lists the server's services, sites, jobs, ports or processes
    r"systemctl\b[^;&|\n]*\blist-(?:units|timers|unit-files|sockets|dependencies|jobs)\b|\bcrontab\b|server_name"
    r"|/etc/(?:nginx|caddy|apache2|cron|systemd)|/var/spool/cron|sites-(?:enabled|available)|\bnginx\s+-T"
    r"|\bcertbot\s+certificates|/etc/letsencrypt/(?:live|renewal|archive)\b(?!/(?:kyianyn-routine|livii-bereh))"
    r"|(?<![\w./\-])(?:ss|netstat|lsof)(?=\s+-|\s*(?:$|[|;&)]))|\bdocker\s+(?:compose\s+|container\s+)?(?:ps|ls)\b"
    r"|(?:^|[;&|(`]|\$\()\s*(?:sudo\s+)?(?:ps|pstree)\b(?!\s*[=(.\[])|\bpgrep\s+(?:-\w+\s+)*-[A-Za-z]*[al][A-Za-z]*\b"
    r"|\b(?:top|htop)\s+-b|\bsystemctl(?:\s+--?[\w\-=]+)*\s*(?=$|[|;&)>])|\bservice\s+--status-all"
    r"|(?<![\w.\-])/etc/?(?=$|[\s;&|)'\"*])"
    r"|\bjournalctl\b(?![^;&|\n]*(?:-u|--unit)[\s=]+['\"]?(?:kyianyn-routine|livii-bereh))"
    r"|(?<![\w.\-])/home/?(?![\w.\-/])|/home/(?!ye\b)[\w.\-]|(?<![\w.\-])/root\b|/var/www/?(?![\w.\-/])"
    r"|/var/www/(?!kyianyn-routine|livii-bereh)[\w.*\-]|(?:~|/home/ye)/PROJECTS/?(?![\w.\-/])|(?:~|/home/ye)/PROJECTS/[*?{]",
    re.M)
SKILL_LINE = re.compile(r"Base directory for this skill:\s*([/~]\S*)[^\n]*")  # a skill body quoted in a tool output
HOME = r"(?:~|\$HOME|\$\{HOME\}|/home/[\w.\-]+|/root)"
HOME_DOT = re.compile(rf"{HOME}/\.(?!(?:claude/projects|cache|npm)(?![\w\-]|\.\w))[\w.\-]+(?:/[^\s\"'`<>()\[\]{{}},;|&]*)?")
# a path into a dot-folder of the home directory (settings, skills, secrets) is private, but projects, cache and npm
OWN_DIR = rf"{HOME}/\.(?:agent|claude(?!/projects(?![\w.\-])))(?![\w.\-])"  # the author's agent rules and skills
HOME_NAME = re.compile(rf"{HOME}/\.([\w\-]+)")  # the name of a dot-folder the sessions show in a home directory
READS = re.compile(r"\b(?:cat|sed|head|tail|less|more|bat|awk|nl)\b[^;&|\n]*?(?:SKILL|AGENTS|CLAUDE)\.md"
                   r"|(?<![\w.\-])(?:cat|sed|head|tail|less|more|bat|awk|nl|grep|egrep|rg|ls|find|tree|wc|stat|du|cd|diff"
                   rf"|file|jq)\b[^;&|\n]*?{OWN_DIR}")
FINDING = re.compile(r"chats/\d{2}-\S*?[\s|:,]+\d+[\s|,]+[A-Za-z][\w\-]*\s*\|")  # a privacy review row: a chat file, a line, a kind |
SUBAGENT = re.compile(r"journal\.jsonl|\bsubagents\b|(?<![\w.\-])[wa][a-z0-9]{8}\.output\b")
# what subagents wrote: a workflow's journal, a session's subagents folder, a workflow's or agent's task output
VAULT = re.compile(r"\b[Vv]ault\s+(?:push|run|approve|edit|unlock|lock|import|export|rm|open|add|set|get|list|ls|status"
                   r"|check|revoke|rotate)\b|\bPIN\b")  # the vault's commands and PIN (vault call stays)
MAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}")
IPV4 = re.compile(r"(?<!\d)(?:\d{1,3}\\{0,2}\.){3}\d{1,3}(?!\d)")  # dots escaped in a regex or in JSON too
IPV6 = re.compile(r"(?<![\w:])(?:[0-9A-Fa-f]{0,4}:){3,7}[0-9A-Fa-f]{0,4}(?![\w:])")
PHONE_RE = re.compile(r"(?<![\w+])(?:\+380[ \-]?\(?\d{2}\)?[ \-]?|\(?0\d{2}\)?[ \-]|\+\d{1,3}[ \-]\(?\d{2,3}\)?[ \-])"
                      r"\d{3}[ \-]?\d{2}[ \-]?\d{2}(?!\d)")
TOKEN = re.compile(r"[A-Za-z0-9_+/=\-]{24,}")
TOKEN_CHARS = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_+/=-")
GUARD_CHARS = TOKEN_CHARS - {"/"}  # a fragment cut stops at a path separator
WORDY = re.compile(r"(?:[A-Z]?[a-z]+|[A-Z]+)*[0-9]*|[0-9]+[A-Za-z]{0,3}|[0-9a-f]{1,12}|[0-9]+(?:[A-Za-z][0-9]+)*[A-Za-z]?")
# a word, a number, short hex or a compact time such as 20261011T081530Z
UUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
SENTINEL = re.compile("\x00(\\d+)\x00")
REMINDER = re.compile(r"<system-reminder>.*?(?:</system-reminder>|\Z)", re.S)
PASTED = re.compile(r"<pasted_content\b[^>]*>(.*?)</pasted_content[^>]*>", re.S)


def entropy(t):
    return -sum(c / len(t) * math.log2(c / len(t)) for c in Counter(t).values())


def wordy(part):
    return all(WORDY.fullmatch(p) for p in re.split(r"[_+=\-]+", part) if p)


def secretish(t):
    """A 24+ character token mixing upper case, lower case and digits with 4+ bits per character, not a UUID or pure
    hex: a path made of words is cut too (strict on purpose; the review file lists every such cut)."""
    return (len(t) >= 24 and not UUID.fullmatch(t) and not re.fullmatch(r"[0-9a-fA-F]+", t)
            and bool(re.search("[A-Z]", t) and re.search("[a-z]", t) and re.search("[0-9]", t)) and entropy(t) >= 4.0)


def randomish(part):
    """A path part of 16+ characters with letters and digits, not made of words and numbers, 3+ bits per character
    (a random id inside a path that passes as a whole)."""
    return (len(part) >= 16 and not wordy(part) and not UUID.fullmatch(part) and not re.fullmatch(r"[0-9a-fA-F]+", part)
            and bool(re.search("[0-9]", part) and re.search("[A-Za-z]", part)) and entropy(part) >= 3.0)


def word_path(t):
    """A path, not a key: a slash, every piece between / . - _ a word of at most 15 characters (letters, digits may
    follow) or under 3.5 bits per character, and at least one plain word of 3 or more small letters (a random key with
    a slash in it has none)."""
    pieces = [p for p in re.split(r"[/._\-]+", t) if p]
    return ("/" in t and any(re.fullmatch("[a-z]{3,}", p) for p in pieces)
            and all(len(p) <= 15 and re.fullmatch("[A-Za-z]+[0-9]*", p) or entropy(p) < 3.5 for p in pieces))


def inventory(command):
    """True when a shell command lists the server's services, sites, jobs, ports or processes (its whole output is
    cut): systemctl status counts too, unless it names exactly one unit and that unit is this project's (kyianyn-routine, before it livii-bereh)."""
    if INVENTORY.search(command):
        return True
    for m in re.finditer(r"systemctl\s+(?:--?[\w\-=]+\s+)*status\b([^;&|\n]*)", command):
        units = []
        for word in m.group(1).split():
            if re.match(r"[0-9]*[<>]", word):
                break
            if not word.startswith("-"):
                units.append(word.strip("'\""))
        if len(units) != 1 or not units[0].startswith(("kyianyn-routine", "livii-bereh")):
            return True
    return False


def unquoted(command):
    """The command with ; & | inside quotes or after a backslash blanked, so a pattern such as grep 'a\\|b' does not
    end the command before the path it reads."""
    return re.sub(r"'[^'\n]*'|\"(?:[^\"\\\n]|\\.)*\"|\\[;&|]", lambda m: re.sub("[;&|]", " ", m.group(0)), command)


def other_unit(line):
    """True when a line names a systemd service or timer that is neither this project's nor a stock one."""
    return any(not OWN_UNIT.fullmatch(m.group(1)) for m in UNIT.finditer(line))


def parts(word):
    """The parts of a private word: split at - _ . and spaces, at camelCase, between letters and digits and around any
    other character."""
    return [p for chunk in re.split(r"[-_. ]+", word)
            for p in re.findall(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|[0-9]+|[^A-Za-z0-9]+", chunk)]


class Redactor:
    """redact() and what it keeps: counts per kind, the cut values for the fragment pass, high-entropy cuts for review."""

    def __init__(self, words, guards=(), sites=()):
        alts = "|".join(SEP.join(map(re.escape, parts(w))) for w in sorted(words, key=len, reverse=True) if parts(w))
        self.private = re.compile(rf"(?i)(?<![\w.\-])[\w.\-]*?(?:{alts})[\w.\-]*(?<!\.)") if alts else None
        # how the server and the keys are guarded: regular expressions from --deny, so the repo does not list them
        self.security = re.compile("(?i)" + "|".join(guards)) if guards else None
        # the names of the server's other sites: common words, so only a line naming two of them (a list of the sites)
        # or one next to True or False (a check of the list) is cut
        self.sites = re.compile(r"(?i)(?<![\w\-])(?:" + "|".join(map(re.escape, sites)) + r")(?![\w\-])") if sites else None
        self.values, self.review, self.count, self.file, self.relative = set(), [], Counter(), "", None

    def learn(self, texts):
        """The dot-folders the sessions show in a home directory (~/.name): a path that starts with one of them without
        ~/ (.claude/skills, as a command run from the home directory prints it) is private too; .claude/projects,
        .cache, .npm and the project's own dot-entries (.git, .venv) stay."""
        own = {p.name[1:] for p in ROOT.iterdir() if p.name.startswith(".")} - {"agent", "claude"}
        names = {n for t in texts for n in HOME_NAME.findall(t)} - own - {"cache", "npm"}
        alts = "|".join(map(re.escape, sorted(names, key=len, reverse=True)))
        self.relative = re.compile(rf"(?<![\w~$}}.\-])(?<![\w~}}\-]/)\.(?!claude/projects(?![\w.\-]))(?:{alts})"
                                   rf"(?![\w\-])[\w.\-]*(?:/[^\s\"'`<>()\[\]{{}},;|&]*)?") if alts else None

    def cut(self, kind, value, remember=False):
        """The mark for value; a key found by its own pattern is remembered for the fragment pass."""
        self.count[kind] += 1
        if remember and len(value) >= 12:
            self.values.add(value)
        return MARK[kind]

    def named(self, m):
        """The name kept and its value cut, whatever the value is, except on the Co-Authored-By line and a plain code
        value (True, a number, lambda, a name made of words) after key, keys or sort_keys; a value already cut stays."""
        head, value = m.group(1), m.group(2)
        bare = value.strip("\"'`")
        name = re.search(rf"(?i)[\w.\-]*{NAMES}[\w.\-]*", head).group(0).strip("-").lower()
        if (not bare or bare.startswith("[REDACTED") or name == "co-authored-by"
                or name in KEEP_NAMES and bare == value and CODE.fullmatch(value)):
            return m.group(0)
        quote = value[0] if value[0] in "\"'`" else ""
        return head + quote + self.cut(KEY, bare) + quote

    def bracketed(self, text):
        """A bracketed value after a key name, such as auth=("user", "pass") or a dict of cookies, cut whole up to its
        closing bracket, nested ones and line breaks included; one that never closes is cut to the end of the text. A
        tuple or list of names or short words after key, keys or sort_keys stays."""
        out, at = [], 0
        for m in OPEN.finditer(text):
            start = m.end(1)
            if m.start() < at or text.startswith("[REDACTED", start):
                continue
            depth, end = 0, len(text)
            for i in range(start, len(text)):
                depth += (text[i] in "([{") - (text[i] in ")]}")
                if not depth:
                    end = i + 1
                    break
            name = re.search(rf"(?i)[\w.\-]*{NAMES}[\w.\-]*", m.group(1)).group(0).strip("-").lower()
            if name in KEEP_NAMES and ITEMS.fullmatch(text[start:end]):
                continue
            out += [text[at:start], self.cut(KEY, text[start:end])]
            at = end
        return "".join(out) + text[at:]

    def ipv4(self, m):
        return m.group(0) if m.group(0).replace("\\", "") in ALLOWED_IPS else self.cut(IP, m.group(0))

    def ipv6(self, m):
        groups = [g for g in m.group(0).split(":") if g]
        if len(groups) < 4 or m.group(0).count("::") > 1 or not ("::" in m.group(0) or any(len(g) >= 3 for g in groups)):
            return m.group(0)
        return self.cut(IP, m.group(0))

    def high(self, t):
        """The mark for a high-entropy cut, noted for the review (resolve() fills in its output line)."""
        self.count[ENT] += 1
        self.review.append([self.file, None, t[:3], len(t)])
        return f"[REDACTED: ключ\x00{len(self.review) - 1}\x00]"

    def token(self, m):
        """A token cut whole by the rule unless it is a path made of words; a random-looking part of a path is cut."""
        t = m.group(0)
        if secretish(t) and not word_path(t):
            return self.high(t)
        return "/".join(self.high(p) if secretish(p) or randomish(p) else p for p in t.split("/")) if "/" in t else t

    def redact(self, text, tool=False, result=False):
        """text with every private path, key, IP, e-mail, phone and private word cut. In any text a vault command, the
        PIN, a detail of how the server and the keys are guarded or a row of the privacy review cuts its whole line; in
        tool text so do a private word and server_name, and in a tool result a systemd service or timer of another
        project."""
        text = HOME_DOT.sub(lambda m: self.cut(PATH, m.group(0)), text.replace("\x00", ""))
        if self.relative:
            text = self.relative.sub(lambda m: self.cut(PATH, m.group(0)), text)
        for rx in KEYS:
            text = rx.sub(lambda m: self.cut(KEY, m.group(0), True), text)
        for rx in KEEP:
            text = rx.sub(lambda m: m.group(1) + self.cut(KEY, m.group(2), True), text)
        text = self.bracketed(text)
        for rx in NAMED + [FLAG]:
            text = rx.sub(self.named, text)
        text = MAIL_RE.sub(lambda m: m.group(0) if m.group(0).lower() in ALLOWED_MAILS else self.cut(MAIL, m.group(0)), text)
        text = IPV4.sub(self.ipv4, text)
        text = PHONE_RE.sub(lambda m: self.cut(PHONE, m.group(0)), IPV6.sub(self.ipv6, text))
        lines = text.split("\n")
        for i, line in enumerate(lines):
            named = {m.group(0).lower() for m in self.sites.finditer(line)} if self.sites else set()
            kind = (PRIV if tool and self.private and self.private.search(line)
                    or len(named) > 1 or named and re.search(r"\b(?:True|False)\b", line)
                    else SERVER if tool and ("server_name" in line or result and other_unit(line))
                    else REVIEW if FINDING.search(line)
                    else SAFE if self.security and self.security.search(line) or VAULT.search(line) else None)
            if kind:
                lines[i] = SAFE_MARK if kind == SAFE else REVIEW_MARK if kind == REVIEW else LINE_MARK
                self.count[kind] += 1
        text = "\n".join(lines)
        if not tool and self.private:
            text = self.private.sub(lambda m: self.cut(PRIV, m.group(0)), text)
        return TOKEN.sub(self.token, text)

    def dirty(self, text):
        """True when redact() would change text; nothing is counted or kept for the review."""
        kept = self.count, self.review, self.values
        self.count, self.review, self.values = Counter(), [], set()
        changed = self.redact(text) != text
        self.count, self.review, self.values = kept
        return changed

    def guard(self, text):
        """Cut every token that still holds an 8-character piece of a key cut by its pattern (a key split by a line break)."""
        chunks = {c for v in self.values for c in (v[i:i + 8] for i in range(0, len(v) - 7, 4))
                  if set(c) <= TOKEN_CHARS and ((re.search("[0-9]", c) and re.search("[A-Za-z]", c))
                                                or (re.search("[A-Z]", c) and re.search("[a-z]", c)))}
        spans = []
        for i in (i for i in range(len(text) - 7) if text[i:i + 8] in chunks):
            a, b = i, i + 8
            while a > 0 and text[a - 1] in GUARD_CHARS:
                a -= 1
            while b < len(text) and text[b] in GUARD_CHARS:
                b += 1
            if spans and a <= spans[-1][1]:
                spans[-1][1] = max(spans[-1][1], b)
            else:
                spans.append([a, b])
        self.count[FRAG] += len(spans)
        for a, b in reversed(spans):
            text = text[:a] + MARK[FRAG] + text[b:]
        return text

    def resolve(self, text, name):
        """Note the output line of every high-entropy cut for the review and drop the line markers."""
        lines = text.split("\n")
        for no, line in enumerate(lines, 1):
            for m in SENTINEL.finditer(line):
                self.review[int(m.group(1))][:2] = [name, no]
        return SENTINEL.sub("", text)


def kyiv(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(KYIV)


def when(ts, fmt):
    return f"{kyiv(ts):{fmt}}" if ts else "?"


def content(e):
    return (e.get("message") or {}).get("content")


def plural(n, one, few, many):
    return one if n % 10 == 1 and n % 100 != 11 else few if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else many


def clip(text, limit):
    """text cut to limit characters, at a space when one is near, never inside a mark or an e-mail."""
    if len(text) <= limit:
        return text
    cut = text[:limit]
    space = max(cut.rfind(" "), cut.rfind("\n"))
    if not text[limit].isspace() and space > limit - 200:
        cut = cut[:space]
    at = cut.rfind("[REDACTED")
    cut = cut[:at] if at >= 0 and "]" not in cut[at:] else cut
    return re.sub(r"[\w.%+\-]+@[\w.\-]*$", "", cut)


def window(text, size):
    """The first size characters without a token cut in two at the end (half a key is still a key)."""
    return text if len(text) <= size else re.sub(r"[A-Za-z0-9_+/=\-]+\Z", "", text[:size])


def trim(text, limit, red, tool=True):
    """text redacted over a window wider than the limit (a key on the edge is still seen whole), then cut to it."""
    shown = clip(red.redact(window(text, limit + 2000), tool), limit)
    return DANGLING.sub("", shown) + f"\n... ще {len(text) - limit} символів" if len(text) > limit else shown


def fenced(text):
    run = max((len(r) for r in re.findall("`+", text)), default=0)
    fence = "`" * max(3, run + 1)
    return f"{fence}\n{text}\n{fence}"


def inline(text):
    """One line of plain text safe inside bold or italic Markdown."""
    return re.sub(r"([\\*_`<>])", r"\\\1", " ".join(text.split()))


def italic(text):
    return f"*{inline(text)}*\n"


def quote(text):
    """User text as a Markdown quote: < and > escaped, line breaks kept, pasted text as a nested quote."""
    lines = []
    for i, part in enumerate(PASTED.split(text)):
        if not part.strip():
            continue
        if i % 2:
            lines.append("**«вставлений текст»:**")
        lines += [("> " if i % 2 else "") + line.replace("<", "&lt;").replace(">", "&gt;") for line in part.strip("\n").split("\n")]
    return "\n".join(f"> {line}  " if line.strip() else ">" for line in lines)


def markdown(text):
    """Claude's text as Markdown with tag-like < escaped outside code and every code fence closed."""
    out, fence = [], None
    for line in text.split("\n"):
        m = re.match(r"\s*(`{3,}|~{3,})", line)
        if fence:
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence) and not line.strip().strip(fence[0]):
                fence = None
        elif m:
            fence = m.group(1)
        else:
            line = "".join(p if p.startswith("`") else re.sub(r"<(?=[A-Za-z/!?])", "&lt;", p)
                           for p in re.split(r"(`+[^`]*`+)", line))
        out.append(line)
    return "\n".join(out + ([fence] if fence else []))


def tool_call(p, red):
    """A bold line with the tool and its description or path, then its input in a fence."""
    name, inp = p.get("name") or "?", p.get("input") or {}
    path = str(inp.get("file_path") or inp.get("path") or "")
    if name in ("Bash", "Monitor"):
        head, body = inp.get("description") or "", trim(str(inp.get("command") or ""), 1500, red)
    elif name == "Read":
        span = f", рядки від {inp.get('offset', 1)}, до {inp.get('limit', 'кінця')}" if inp.get("offset") or inp.get("limit") else ""
        head, body = path, red.redact(path + span, True)
    elif name == "Edit":
        head = path
        body = (f"файл: {red.redact(path, True)}\n--- було:\n{trim(str(inp.get('old_string') or ''), 600, red)}\n"
                f"--- стало:\n{trim(str(inp.get('new_string') or ''), 600, red)}")
    elif name == "Write":
        text = str(inp.get("content") or "")
        head, body = path, f"файл: {red.redact(path, True)}, {len(text)} символів\n{trim(text, 1500, red)}"
    elif name in ("Agent", "Task", "Workflow"):
        head = inp.get("description") or inp.get("scriptPath") or ""
        text = str(inp.get("prompt") or inp.get("script") or "")
        if inp.get("args"):
            text += "\n\nargs: " + json.dumps(inp["args"], ensure_ascii=False, indent=1)
        body = trim(text or json.dumps(inp, ensure_ascii=False, indent=1), 1500, red)
    else:
        head, body = inp.get("description") or path, trim(json.dumps(inp, ensure_ascii=False, indent=1), 1000, red)
    line = f"**{inline(name)}**" + (f": {inline(clip(red.redact(str(head), True), 200))}" if head else "")
    return f"{line}\n\n{fenced(body)}\n"


def instructions(call):
    """None, or the names of the files a tool call reads when they are instructions, not the conversation: SKILL.md,
    AGENTS.md or CLAUDE.md, or anything in the author's rules and skills (~/.claude outside projects, ~/.agent) read by
    Read, Grep or Glob, or by cat, sed, ls, grep, cd and the like in Bash (a | inside quotes does not end the command)."""
    name, inp = (call or {}).get("name"), (call or {}).get("input") or {}
    if name in ("Read", "Grep", "Glob"):
        paths = [str(inp.get("file_path") or inp.get("path") or "")]
        if not (re.match(OWN_DIR, paths[0]) or name == "Read" and Path(paths[0]).name in INSTRUCTION_FILES):
            return None
    elif name in ("Bash", "Monitor") and READS.search(unquoted(str(inp.get("command") or ""))):
        command = str(inp.get("command"))
        paths = re.findall(r"[\w.~/\-]*(?:SKILL|AGENTS|CLAUDE)\.md\b", command) + [
            m.group(0) for m in HOME_DOT.finditer(command) if re.match(OWN_DIR, m.group(0))]
    else:
        return None
    names = [f"{Path(p).parent.name}/{Path(p).name}" if Path(p).name == "SKILL.md" and Path(p).parent.name
             else Path(p.rstrip("/*")).name for p in paths]
    names = [n for n in dict.fromkeys(names) if n and not n.startswith(".") and not re.search(r"[*?{]", n)]
    return ", ".join(names[:4]) + (f" та ще {len(names) - 4}" if len(names) > 4 else "")


def subagent_output(call):
    """True when a tool call reads what subagents wrote: a workflow journal.jsonl, a session's subagents folder or a
    workflow's task output. Their conversations stay out, and their findings can retell what is cut elsewhere."""
    name, inp = (call or {}).get("name"), (call or {}).get("input") or {}
    if name in ("Bash", "Monitor"):
        return bool(SUBAGENT.search(str(inp.get("command") or "")))
    return name in ("Read", "Grep", "Glob") and bool(SUBAGENT.search(str(inp.get("file_path") or inp.get("path") or "")))


def tool_result(p, red, call=None):
    """The tool output folded: at most 40 lines and 3000 characters, then how many lines are left. A skill body, the
    text of instructions the call read or what subagents wrote becomes one italic line, and the output of a command
    that lists the server's services, sites or jobs one mark."""
    c = p.get("content")
    if isinstance(c, list):
        c = "\n".join(q.get("text") or "" if q.get("type") == "text" else "[зображення]" if q.get("type") == "image"
                      else f"[{q.get('type')}]" for q in c if isinstance(q, dict))
    text = REMINDER.sub("", str(c or "")).strip("\n")
    if not text.strip():
        return italic("помилка без тексту" if p.get("is_error") else "результат порожній")
    read = None if p.get("is_error") else instructions(call)
    if text.startswith("Base directory for this skill:") or read is not None:
        return italic(red.redact(f"прочитано інструкції {read}".strip() if read is not None else meta_line(text)))
    if subagent_output(call):
        return italic("прочитано вивід субагентів, не включено")
    text = SKILL_LINE.sub(lambda m: "завантажено навичку " + Path(m.group(1)).name, text)
    total, seen = text.count("\n") + 1, window(text, 5000)
    label = ("помилка, " if p.get("is_error") else "результат: ") + f"{total} {plural(total, 'рядок', 'рядки', 'рядків')}"
    if (call or {}).get("name") in ("Bash", "Monitor") and inventory(str((call.get("input") or {}).get("command") or "")):
        red.count[SERVER] += 1
        return f"<details><summary>{label}</summary>\n\n{fenced(SERVER_MARK)}\n\n</details>\n"
    lines = red.redact(seen, True, True).split("\n")  # a cut over several lines leaves one
    shown = clip("\n".join(lines[:40]), 3000)
    left = len(lines) + text.count("\n", len(seen)) - shown.count("\n") - 1
    more = f"\n... ще {left} {plural(left, 'рядок', 'рядки', 'рядків')}\n" if left > 0 else ""
    return f"<details><summary>{label}</summary>\n\n{fenced(shown)}\n{more}\n</details>\n"


def meta_line(text):
    """One line for text Claude Code injects (a skill body, a caveat, an image note)."""
    m = re.match(r"Base directory for this skill:\s*(\S+)", text)
    if m:
        return f"завантажено навичку {Path(m.group(1)).name}"
    if "<local-command-caveat>" in text:
        return "службова примітка Claude Code про локальні команди"
    m = re.search(r"<command-(?:name|message)>/?([^<]+)<", text)
    if m:
        return f"завантажено команду {m.group(1).strip()}"
    if text.startswith("Image") or "[Image" in text:
        return "службовий опис зображення"
    return f"службовий текст Claude Code, {len(text)} символів"


def user_text(c):
    """The text of a user entry or queued prompt (images as [зображення]) and its tool results."""
    parts = [{"type": "text", "text": c}] if isinstance(c, str) else [p for p in c or [] if isinstance(p, dict)]
    texts = [p.get("text") or "" if p.get("type") == "text" else "[зображення]" for p in parts if p.get("type") in ("text", "image")]
    return REMINDER.sub("", "\n".join(texts)).strip(), [p for p in parts if p.get("type") == "tool_result"]


def summary(text, red):
    """A context compaction summary, folded; redact() cuts a line with a vault command, the PIN or a detail of how the
    server is guarded whole, as in any text."""
    return f"<details><summary>Підсумок стиснутого контексту</summary>\n\n{fenced(red.redact(text))}\n\n</details>\n"


def user_block(ts, text, red, n, queued=False):
    """A user message (rendered and counted), or one italic line for a notification, a slash command or its output,
    or a folded summary."""
    m = re.search(r"<summary>(.*?)</summary>", text, re.S)
    if text.startswith("<task-notification"):
        return italic(red.redact("сповіщення про фонове завдання: " + (m.group(1) if m else "завершено")))
    if text.startswith(("<local-command-stdout", "<local-command-stderr")):
        out = re.sub(r"</?local-command-std(?:out|err)>", "", text).strip()
        out = clip(red.redact(window(out, 2000), True), 200)
        return italic("вивід команди: " + out if out else "вивід команди порожній")
    if text.startswith("<local-command-caveat"):
        return italic("службова примітка Claude Code про локальні команди")
    if text.startswith("[Request interrupted"):
        return italic("перервано користувачем")
    if text.startswith("This session is being continued from a previous conversation"):
        return summary(text, red)
    cmd = re.search(r"<command-name>(.*?)</command-name>", text, re.S)
    if cmd:  # a slash command such as /clear is one italic line, not a user message
        args = re.search(r"<command-args>(.*?)</command-args>", text, re.S)
        return italic(red.redact(f"команда {cmd.group(1).strip()} {args.group(1).strip() if args else ''}"))
    if text.startswith("Base directory for this skill:"):
        return italic(red.redact(meta_line(text)))
    n["user"] += 1
    head = f"### Користувач, {when(ts, '%d.%m %H:%M')}" + (" (надіслано під час роботи)" if queued else "")
    return f"{head}\n\n{quote(red.redact(text))}\n"


def render(s, red):
    """The Markdown body of one session and its counts: user messages, Claude replies, tool calls, thinking skipped."""
    n, out, shown = Counter(), [], set()
    results = {p.get("tool_use_id"): p for e in s["entries"] if e.get("type") == "user"
               for p in user_text(content(e))[1]}
    calls = {p.get("id"): p for e in s["entries"] if e.get("type") == "assistant" and isinstance(content(e), list)
             for p in content(e) if isinstance(p, dict) and p.get("type") == "tool_use"}
    for e in s["entries"]:
        kind, ts = e.get("type"), e.get("timestamp")
        if kind == "assistant":
            c = content(e)
            for p in c if isinstance(c, list) else [{"type": "text", "text": c or ""}]:
                if p.get("type") in ("thinking", "redacted_thinking"):
                    n["thinking"] += 1
                elif p.get("type") == "text" and REMINDER.sub("", p.get("text") or "").strip():
                    n["claude"] += 1
                    out.append(f"### Claude, {when(ts, '%H:%M')}\n\n{markdown(red.redact(REMINDER.sub('', p['text']).strip()))}\n")
                elif p.get("type") == "tool_use":
                    n["tools"] += 1
                    out.append(tool_call(p, red))
                    if p.get("id") in results:
                        shown.add(p.get("id"))
                        out.append(tool_result(results[p.get("id")], red, p))
        elif kind == "user":
            text, res = user_text(content(e))
            for p in res:
                if p.get("tool_use_id") not in shown:
                    shown.add(p.get("tool_use_id"))
                    out.append(tool_result(p, red, calls.get(p.get("tool_use_id"))))
            if not text:
                continue
            if e.get("isMeta"):
                out.append(italic(red.redact(meta_line(text))))
            elif e.get("isCompactSummary"):
                out.append(summary(text, red))
            elif (e.get("origin") or {}).get("kind") == "task-notification" and not text.startswith("<task-notification"):
                out.append(italic(red.redact("сповіщення про фонове завдання")))
            else:
                out.append(user_block(ts, text, red, n))
        elif kind == "attachment" and (e.get("attachment") or {}).get("type") == "queued_command":
            a = e["attachment"]
            text = user_text(a.get("prompt"))[0]
            if a.get("commandMode") == "task-notification" or text.startswith("<task-notification"):
                out.append(user_block(ts, text if text.startswith("<task-notification") else "<task-notification>", red, n))
            elif text:
                out.append(user_block(ts or a.get("timestamp"), text, red, n, queued=True))
    return "\n".join(out), n


def load(path, red):
    """One session: its non-sidechain entries in file order (a line still being written is skipped), times, topic and
    file slug. A session missing from TOPICS takes its last ai-title, redacted (the cut counts for its file), and a slug
    made of what is left of it, or 'chat' when the slug itself would be cut."""
    entries = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if isinstance(e, dict) and not e.get("isSidechain"):
                entries.append(e)
    times = [e["timestamp"] for e in entries if isinstance(e.get("timestamp"), str)]
    titles = [e["aiTitle"] for e in entries if e.get("type") == "ai-title" and e.get("aiTitle")]
    red.count = Counter()
    topic, slug = TOPICS.get(path.stem[:8]) or (red.redact(str(titles[-1]) if titles else "без назви"), "")
    if not slug:
        slug = re.sub(r"[^a-z0-9]+", "-", re.sub(r"\[REDACTED[^\]]*\]", " ", topic).lower()).strip("-")[:60].strip("-")
        slug = slug if slug and not red.dirty(slug) else "chat"
    return {"sid": path.stem, "entries": entries, "topic": topic, "slug": slug, "count": red.count,
            "start": kyiv(times[0]) if times else None, "end": kyiv(max(times)) if times else None}


def header(i, s, n, names):
    """The title, Kyiv time span, session id, counts and links to the next and previous chats."""
    a, b = s["start"], s["end"]
    span = f"{a:%d.%m.%Y}, {a:%H:%M} до {b:%H:%M}" if a.date() == b.date() else f"{a:%d.%m.%Y %H:%M} до {b:%d.%m.%Y %H:%M}"
    links = ([f"[← Чат {i - 1:02d}]({names[i - 2]})"] if i > 1 else []) + ["[усі чати](all-chats.md)"] + (
        [f"[Чат {i + 1:02d} →]({names[i]})"] if i < len(names) else [])
    return (f"# Чат {i:02d}: {s['topic']}\n\n{span} за київським часом, сесія {s['sid'][:8]}\n\n"
            f"Повідомлень користувача: {n['user']} | відповідей Claude: {n['claude']} | викликів інструментів: "
            f"{n['tools']} | прихованих міркувань пропущено: {n['thinking']}\n\n{' | '.join(links)}\n")


def readme(rows):
    table = "\n".join(f"| {i:02d} | [{name}]({name}) | {s['start']:%d.%m.%Y %H:%M} | {SENTINEL.sub('', s['topic'])} |"
                      for i, (name, s, n) in enumerate(rows, 1))
    return f"""# Чати з Claude Code

Повний текстовий експорт розмов з ШІ-інструментом (Claude Code), у яких зроблено цей проєкт.

## Файли і порядок

Один файл на одну сесію Claude Code, у часовому порядку (за першим записом сесії, київський час). Файл
[all-chats.md](all-chats.md) містить усі сесії підряд, на початку зміст.

| № | файл | початок | тема |
|---|---|---|---|
{table}

## Як читати

- «Користувач, 10.10 15:21»: повідомлення автора, дослівно, у вигляді цитати. «(надіслано під час роботи)»: написане,
  поки Claude ще працював.
- «Claude, 15:22»: відповідь Claude.
- Жирний рядок з назвою інструмента (Bash, Read, Edit, Write, Workflow та інші): виклик, під ним його вхід.
- «результат: N рядків»: згорнутий вивід інструмента, натисніть, щоб розгорнути.
- Рядки курсивом: службові події (завантажено навичку, прочитано інструкції, прочитано вивід субагентів, команда,
  сповіщення про фонове завдання).

## Що вирізано і чому

- Приховані міркування Claude (thinking): у шапці кожного чату є їх кількість.
- Системні нагадування (system-reminder) і службові записи Claude Code: це не частина розмови.
- Тексти навичок і файлів інструкцій (SKILL.md, AGENTS.md, CLAUDE.md) і все прочитане з тек автора з його правилами
  й навичками: це теж не розмова, замість тексту один рядок курсивом «завантажено навичку ...» або «прочитано
  інструкції ...».
- Вивід інструментів обрізано до 40 рядків і 3000 символів, вхід до 1500 символів (Edit: до 600 на кожен бік).
- Розмови субагентів не включено: їх завдання видно у викликах Agent і Workflow, а підсумок у результатах цих
  викликів і у словах Claude. Вивід команди, яка читає журнал воркфлоу (journal.jsonl), теку субагентів чи файл виводу
  воркфлоу, замінено рядком курсивом «прочитано вивід субагентів, не включено»: їх знахідки бувають переказом
  вирізаного.
- Ключі, токени, паролі, IP-адреси, e-mail (крім yisakov@kse.org.ua і noreply@anthropic.com у рядках Co-Authored-By),
  телефони, слова про інші приватні проєкти автора, шляхи до прихованих тек у домашній теці автора, перелік служб,
  сайтів і процесів сервера, на якому є й інші проєкти, подробиці того, як захищено сервер і сховище ключів, і рядки
  таблиці огляду приватності, які переказують вирізане: репозиторій публічний.

## Позначки

- `[REDACTED: ключ]`: ключ API, токен, пароль або інший рядок, схожий на секрет. Правило навмисно строге: вирізано
  кожне значення після назви з key, token, secret, password, passwd, pwd, auth, cookie, session чи api_hash, навіть у
  коді і навіть коли назва в лапках, зворотних лапках, дужках чи жирним шрифтом (`` `MAX_TOKENS` = 100 ``,
  `**Password:** ...`), а значення в дужках цілком. Залишено лише рядок Co-Authored-By і прості значення в коді після
  назви, яка точно є key, keys чи sort_keys (у будь-якому регістрі, теж у дужках чи зворотних лапках, як
  `got[key] = x`): True, False, None, число, lambda, назва зі слів або дужки зі списком таких назв чи коротких слів у
  лапках. Так само вирізано кожен довгий рядок з великих і малих літер та цифр; шлях до файлу зі слів залишено, а
  випадковий шматок у ньому вирізано.
- `[REDACTED: перелік служб і сайтів сервера]`: увесь вивід команди, яка показує служби, таймери, сайти, завдання
  cron, порти чи процеси сервера (ps теж) або перелік тек /etc чи /var/www.
- `[REDACTED: рядок про інші приватні проєкти]`: рядок у виклику чи виводі інструмента зі словом про інші приватні
  проєкти або з назвою сайту з конфігурації nginx, а у виводі ще й рядок зі службою чи таймером systemd іншого
  проєкту, вирізано повністю; так само будь-де рядок, що називає два чи більше інших сайти сервера.
- `[REDACTED: рядок про захист сервера і ключів]`: рядок будь-де (повідомлення, відповідь Claude, виклик чи вивід
  інструмента, підсумок стиснутого контексту) з командою чи файлом сховища ключів, його PIN чи іншими подробицями
  того, як захищено сервер і ключі, вирізано повністю.
- `[REDACTED: рядок з огляду приватності]`: рядок таблиці знахідок огляду приватності (файл чату, номер рядка, вид
  знахідки) будь-де, вирізано повністю: він переказує те, що вирізано в іншому місці.
- `[REDACTED: приватний шлях]`: шлях до прихованої теки в домашній теці автора (налаштування, навички, секрети), крім
  ~/.claude/projects, ~/.cache і ~/.npm, теж записаний без ~/ (.claude/skills), як його друкує команда, запущена з
  домашньої теки.
- `[REDACTED]`: слово про інші приватні проєкти в повідомленні (разом з назвою через крапку, як у доменному імені).
- `[REDACTED: IP]`, `[REDACTED: e-mail]`, `[REDACTED: телефон]`: адреса або номер.

## Як оновити

```
.venv/bin/python -I scripts/chats/export.py --deny <список приватних слів> [--review <файл>]
```

Список приватних слів і правил про захист сервера навмисно зберігається поза репозиторієм. Скрипт щоразу переписує цю теку повністю.
"""


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -I scripts/chats/export.py")
    ap.add_argument("--src", type=Path, default=SRC, help="the Claude Code project folder (default %(default)s)")
    ap.add_argument("--out", type=Path, default=OUT, help="the output folder (default %(default)s)")
    ap.add_argument("--deny", type=Path, required=True, help="private words, one per line, # comments, and lines starting with ! (a regular expression: a line it matches "
                         "is cut whole, for how the server and the keys are guarded) or ~ (a name of another site of the server); "
                         "keep it outside the repo")
    ap.add_argument("--review", type=Path, help="write the masked list of high-entropy cuts and the counts here")
    args = ap.parse_args(argv)
    lines = [w.strip() for w in args.deny.read_text(encoding="utf-8").splitlines() if w.strip() and not w.strip().startswith("#")]
    red = Redactor([w for w in lines if w[0] not in "!~"], [w[1:] for w in lines if w[0] == "!"],
                   [w[1:].strip() for w in lines if w[0] == "~"])
    paths = sorted(args.src.glob("*.jsonl"))
    red.learn(p.read_text(encoding="utf-8", errors="replace") for p in paths)
    found = sorted((s for s in (load(p, red) for p in paths) if s["start"]), key=lambda s: s["start"])
    names = [f"{i:02d}-{s['start']:%Y-%m-%d}-{s['slug']}.md" for i, s in enumerate(found, 1)]
    pages, counts = [], []
    for i, (name, s) in enumerate(zip(names, found), 1):
        red.count, red.file = s["count"], name
        body, n = render(s, red)
        pages.append((header(i, s, n, names) + "\n" + body, n))
        counts.append(red.count)
    args.out.mkdir(parents=True, exist_ok=True)
    for old in args.out.glob("*.md"):
        old.unlink()
    texts, report = [], []
    for name, (text, n), count in zip(names, pages, counts):
        red.count = count
        text = red.resolve(red.guard(text), name)
        (args.out / name).write_text(text, encoding="utf-8")
        texts.append(text)
        report.append((name, n, count))
    rows = list(zip(names, found, [n for _, n in pages]))
    contents = "\n".join(f"| [{i:02d}](#chat-{i:02d}) | {s['start']:%d.%m.%Y %H:%M} | {SENTINEL.sub('', s['topic'])} | {n['user']} | "
                         f"{n['claude']} | {n['tools']} | [{name}]({name}) |" for i, (name, s, n) in enumerate(rows, 1))
    whole = ("# Усі чати проєкту\n\nУсі сесії Claude Code підряд, у часовому порядку. Як читати і що вирізано: "
             "[README.md](README.md).\n\n| № | початок | тема | повідомлень користувача | відповідей Claude | "
             "викликів інструментів | окремий файл |\n|---|---|---|---|---|---|---|\n" + contents + "\n\n"
             + "\n\n---\n\n".join(f'<a name="chat-{i:02d}"></a>\n\n{t}' for i, t in enumerate(texts, 1)))
    (args.out / "all-chats.md").write_text(whole, encoding="utf-8")
    (args.out / "README.md").write_text(readme(rows), encoding="utf-8")
    cols = ("КБ", "корист.", "Claude", "інстр.") + KINDS
    print(f"{'файл':<52}" + "".join(f"{c:>10}" for c in cols))
    for name, n, count in report:
        size = (args.out / name).stat().st_size / 1024
        print(f"{name:<52}{size:>10.1f}" + "".join(f"{v:>10}" for v in (n["user"], n["claude"], n["tools"]))
              + "".join(f"{count[k]:>10}" for k in KINDS))
    for name in ("all-chats.md", "README.md"):
        print(f"{name:<52}{(args.out / name).stat().st_size / 1024:>10.1f}")
    total = sum(counts, Counter())
    print("усього вирізано: " + ", ".join(f"{k} {total[k]}" for k in KINDS))
    if args.review:
        lines = ["Огляд вирізаного (scripts/chats/export.py): високоентропійні рядки показано лише першими 3 символами.",
                 "", "Кількість за видом і файлом:"]
        lines += [f"{name}: " + ", ".join(f"{k} {count[k]}" for k in KINDS) for name, _, count in report]
        lines += ["", "Високоентропійні вирізання (файл:рядок, перші 3 символи, довжина):"]
        lines += [f"{f}:{no or 'обрізано'} {head}... довжина {size}" for f, no, head, size in red.review]
        args.review.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
