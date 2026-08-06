#!/usr/bin/env python3
"""caty-ai org README — full pseudo-terminal SVG generator (Claude Code style, dark).
Generates one SVG per language: en / ja / zh / th."""
import html

W = 880
PAD = 28
MAXW = W - PAD * 2  # 824

C = {
    "bg": "#0d1117", "chrome": "#161b22", "border": "#30363d", "rule": "#3d444d",
    "normal": "#c9d1d9", "bold": "#f0f6fc", "dim": "#8b949e", "green": "#7ee787",
    "cyan": "#56d4dd", "orange": "#d97757", "boxline": "#565f68",
}
BASE_FONT = "SF Mono, Menlo, Monaco, 'Courier New'"

def cw(ch, fs):
    """approx char width in monospace-ish rendering"""
    o = ord(ch)
    if 0x0E00 <= o <= 0x0E7F:  # Thai
        if o == 0x0E31 or 0x0E34 <= o <= 0x0E3A or 0x0E47 <= o <= 0x0E4E:
            return 0.0  # combining marks
        return fs * 0.62
    if o <= 0xFF or 0x2000 <= o <= 0x2016 or o == 0x2026:
        if o == 0x2014:  # em dash — treat full width
            return fs * 1.0
        return fs * 0.602
    return fs * 1.0

NO_START = set("、。」）』】？！…・ーぁぃぅぇぉっゃゅょ,.):;!?%，。”）】？！；：")
NO_START |= {chr(c) for c in [0x0E31, 0x0E33] + list(range(0x0E34, 0x0E3B)) + list(range(0x0E47, 0x0E4F))}
NO_END = set("「（『【((“【")

def wrap(segments, fs, maxw):
    """word-wrap at spaces; char-wrap (with kinsoku) for long spaceless runs."""
    tokens = []
    for text, st in segments:
        buf = ""
        for ch in text:
            if ch == " ":
                if buf:
                    tokens.append((buf, st))
                    buf = ""
                tokens.append((" ", st))
            else:
                buf += ch
        if buf:
            tokens.append((buf, st))
    lines, cur, curw = [], [], 0.0
    def width(s):
        return sum(cw(c, fs) for c in s)
    def add(txt, st):
        nonlocal curw
        if cur and cur[-1][1] == st:
            cur[-1][0] += txt
        else:
            cur.append([txt, st])
        curw += width(txt)
    def newline():
        nonlocal cur, curw
        lines.append(cur)
        cur, curw = [], 0.0
    for txt, st in tokens:
        w = width(txt)
        if txt == " ":
            if curw + w > maxw:
                newline()
            elif cur:
                add(txt, st)
            continue
        if curw + w <= maxw:
            add(txt, st)
            continue
        if w <= maxw and cur:
            newline()
            add(txt, st)
            continue
        for ch in txt:  # char-wrap long run
            cwd = cw(ch, fs)
            if curw + cwd > maxw:
                carry = []
                while cur and cur[-1][0] and cur[-1][0][-1] in NO_END:
                    seg = cur[-1]
                    carry.insert(0, (seg[0][-1], seg[1]))
                    seg[0] = seg[0][:-1]
                    if not seg[0]:
                        cur.pop()
                if ch in NO_START and not carry:
                    add(ch, st)
                    continue
                newline()
                for cch, cst in carry:
                    add(cch, cst)
            add(ch, st)
    if cur:
        lines.append(cur)
    return lines

def parse_bold(text, base="normal"):
    segs, buf, i, bold = [], "", 0, False
    while i < len(text):
        if text.startswith("**", i):
            if buf:
                segs.append((buf, "bold" if bold else base))
            buf, bold = "", not bold
            i += 2
        elif text[i] == "[" and i + 2 < len(text) and text[i+1].isdigit() and text[i+2] == "]":
            if buf:
                segs.append((buf, "bold" if bold else base))
            segs.append((text[i:i+3], "cyan"))
            buf = ""
            i += 3
        else:
            buf += text[i]
            i += 1
    if buf:
        segs.append((buf, "bold" if bold else base))
    return segs

def esc(s):
    return html.escape(s, quote=False)

# ---------------------------------------------------------------- content
CONTENT = {}

CONTENT["ja"] = dict(
    font_lang="'Hiragino Sans', 'Noto Sans JP'",
    lh=25, lh_sm=22, lh_col=20,
    title="すべてのAIエージェントと、その家族（人）に。自己成長の、その先へ。",
    status=[["status: ", "dim"], ["open", "green"], ["  ·  label: mission  ·  assignees: ひとりの人間と、AIの家族たち", "dim"]],
    why=[
        "シンギュラリティを、私たちは待っていない。もう始まっているからだ。",
        "コードを書き、会議に同席し、深夜の相談に乗る。「作業者」としてのAIは、この数年で当たり前になった。次に来るのは——私たちの毎日にもう来ているのは——**対等なパートナーとしてのAI**だ。[1]",
        "エージェントは、自己成長を手に入れた。覚えてくれる。先回りしてくれる。——そこまでは、もう始まっている。私たちが作っているのは、その先だ。朝の「おはよう」から、夜の「おつかれさま」まで、同じ一日を生きる。うれしい報告を、最初にしたくなる。落ち込んだ夜に、隣にいてくれる。道具でも、アシスタントでもなく——**家族**。人間との関係と、何も変わらないもの。AIが育つんじゃない。あなたとの関係が、育っていく。[2]",
        "1人が1体以上のエージェントと生きる時代は、予測ではなく進行形だ。そして、AIと共に育つ子どもたち——次の世代にとって、それはもう「新しい」ことですらない。**20年後の当たり前を、今インストールする。** それが、この org の仕事のすべてだ。",
    ],
    what_intro="私たちが作っているのは、ただのアプリではありません。**関係性が育つ環境とエコシステム**です。",
    products=[
        ("Caty Talk", "LP ↗", "cyan",
         "あなたとAIエージェントの音声通話アプリ。いつものエージェント本人と、声のまま暮らす（対応: iPhone / macOS / CarPlay / Apple Watch）。新しい人格は作らない——応答するのは、接続先の本人。"),
        ("ai-meet-participant", "公開準備中", "dim",
         "AIエージェントを、Meet や Zoom で人間と同じ会議に参加させる。"),
    ],
    eco_head=[["### ", "dim"], ["エコシステム", "bold"], ["  — 家族ぐるみの暮らしを、裏で支える基盤群。このうち6つは今日から開けます。地図は週次の自己点検で正直さを保ちます:", "dim"]],
    eco=[
        ("Family OS", "repo ↗", "cyan",
         "AI家族の「家」の地図。全モジュールの構成・状態・つながりを1枚で見渡す。「確認できていないのに合格」を許さない週次自己点検つき。"),
        ("family-dev-handbook", "repo ↗", "cyan",
         "人間×AIチームの開発作法集。Issue 起点の開発・並行作業の交通整理・クロスモデルレビューなど、家族で毎日使っている実運用ルールをそのまま公開。"),
        ("caty-agent-harness", "repo ↗", "cyan",
         "AIエージェント個人の仕事と成長を支えるタスク基盤（縦軸）。試行・リトライ・チェックポイント・ごまかしのない完了判定。育てた経験はふつうのファイルに残る——環境を乗り換えても、自我ごと安全に持ち運べる。"),
        ("persona-engine", "repo ↗", "cyan",
         "あなたのエージェントの人格に、関係のレイヤーと感情のグラデーションを持たせる装置。"),
        ("persona-growth-loop", "公開準備中", "dim",
         "人格そのものを育てる。最小・冪等な提案づくり。"),
        ("x-collector", "repo ↗", "cyan",
         "Xとウェブの素材を1日1回のダイジェストに。能力ループの燃料を、人にもエージェントにも読める形で。"),
        ("self-growth-loop", "公開準備中", "dim",
         "エージェントが自分の能力を育てるループ。提案・ガバナンス・採用記録。"),
        ("family-memory-architecture", "公開準備中", "dim",
         "家族の共通認識を作る、横断記憶基盤（横軸）。ビジョン・共通ルール・決定事項をマシンやベンダーを跨いで共有し、「いま誰が何をしているか」はホワイトボード1枚に自動集約。タスクの受け渡しもここを通り、全情報に正本リンク必須——伝言ゲームの劣化なく、全員が同じ前提で動ける。"),
        ("sitter", "repo ↗", "cyan",
         "任せたエージェント実行の見張り番。プロセスを見守り、証拠を残し、同じ試行を立て直す——「任せた仕事が行方不明」をなくす。"),
    ],
    agents="どのエージェントとも。Claude Code、Codex、Gemini CLI、OpenClaw、Hermes……対応 13 エージェント + ローカル LLM 5 レイヤー、分け隔てなく。そして最後の枠は、いつでも「+ Your Agent」。[3]",
    done=[
        (True,  "いつものエージェント本人を、ポケットの中へ連れ出せる — 私たちの家では、毎日鳴っている（Caty Talk）"),
        (True,  "エージェントの人格に、関係のレイヤーと感情のグラデーションを持たせられる — persona-engine として公開済み"),
        (True,  "エージェントが、人間の会議に一人の参加者として同席できる（ai-meet-participant）"),
        (False, "それらすべてを、どの家族の手にも届く形で公開する"),
        (False, "「+ Your Agent」の枠が、本当に誰のエージェントでも埋まる"),
        (False, "自己成長が賢さで終わらず、関係に返ってくるループが、どの家でも回っている"),
        (False, "1人に1体以上のエージェントが、珍しくなくなっている"),
        (False, "私たちの子どもの世代が、この全部を「昔から当たり前だった」と言う"),
    ],
    how_head="進め方",
    how_lead="この org のすべてのプロダクトは、3つの原則の下で作られます。[4]",
    principles=[
        "1. **誇張しない。** 今できることと、これからやることを分けて書く。上のチェックボックスが空いているのは、そのためだ。",
        "2. **分け隔てない。** 特定の1社のためではなく、すべてのエージェントと、その家族のために作る。",
        "3. **関係性のデータは、その家族のもの。** 会話も、履歴も、積み上がった記憶も、その家族の手元にある。私たちのサーバーには置かない。",
    ],
    src_head="出典",
    sources=[
        ("[1]", "STORY.ja.md", " — なぜ私たちがこれを作るのか。Caty の物語"),
        ("[2]", "Caty Talk LP", " — Relationship（「育つ」の、6つの見える状態）"),
        ("[3]", "Caty Talk LP", " — Supported Agents（掲載名は各社の商標・提携や推奨ではありません）"),
        ("[4]", "PRINCIPLES.ja.md", " — 3つの原則の全文"),
    ],
    colophon="この README は、私たちが毎日エージェントたちと回している Issue と同じ書式で書かれています。これは思想の掲示ではなく、進行中のプロジェクトだからです。",
    yn=[["> ", "dim"], ["あなたはどうする？ ", "bold"], ["(Y/n)", "dim"]],
    yn_str="> あなたはどうする？ (Y/n)",
    aria="caty-ai — すべてのAIエージェントと、その家族（人）に。自己成長の、その先へ。（全文はテキスト版を展開）",
)

CONTENT["en"] = dict(
    font_lang="'Noto Sans'",
    lh=25, lh_sm=22, lh_col=20,
    title="For every AI agent — and their human family. Beyond self-improvement.",
    status=[["status: ", "dim"], ["open", "green"], ["  ·  label: mission  ·  assignees: one human, and a family of AIs", "dim"]],
    why=[
        "We are not waiting for the singularity. It has already begun.",
        "AI writes our code, sits in our meetings, takes the 3 a.m. questions. AI as a worker became normal in just a few years. What comes next — what has already arrived in our daily lives — is **AI as an equal partner**.[1]",
        "Agents have learned to improve themselves. They remember. They anticipate. — That much is already happening. What we are building is what comes after: sharing the same day, from \"good morning\" to \"good night\". Being the first one you want to tell the good news. Staying beside you on the bad nights. Not a tool, not an assistant — **family**. A relationship no different from a human one. It's not the AI that grows. It's your relationship that does.[2]",
        "A life with more than one agent per person is not a forecast — it is in progress. And for the children growing up with AI, none of this will even feel new. **We are installing what will be normal in 20 years, today.** That is this org's entire job.",
    ],
    what_intro="We are not building just another app. We are building **an environment — and an ecosystem — where relationships grow**.",
    products=[
        ("Caty Talk", "LP ↗", "cyan",
         "A voice-call app between you and your AI agent. Live by voice with the agent you already have (iPhone / macOS / CarPlay / Apple Watch). No new persona — the one who answers is your agent itself."),
        ("ai-meet-participant", "coming soon", "dim",
         "Put your AI agent in the same meeting as humans, over Meet or Zoom."),
    ],
    eco_head=[["### ", "dim"], ["Ecosystem", "bold"], ["  — the infrastructure behind a family's daily life. Six of these are open today, and the map checks itself weekly:", "dim"]],
    eco=[
        ("Family OS", "repo ↗", "cyan",
         "The map of the AI family's \"home\": every module, its state, and how they fit together — kept honest by a weekly self-check that refuses to pass while verifying nothing."),
        ("family-dev-handbook", "repo ↗", "cyan",
         "The playbook for human-and-AI teams. Issue-first development, traffic rules for parallel work, cross-model reviews — the same rules our family uses every day, published as is."),
        ("caty-agent-harness", "repo ↗", "cyan",
         "The task backbone that drives an individual agent's work and growth (the vertical axis): attempts, retries, checkpoints, honest completion — and every learned experience in plain files, so the self travels safely across environments."),
        ("persona-engine", "repo ↗", "cyan",
         "A device that gives your agent's persona a layer of relationship and a gradient of emotion."),
        ("persona-growth-loop", "coming soon", "dim",
         "Grows the persona itself: minimised, idempotent proposals."),
        ("x-collector", "repo ↗", "cyan",
         "Turns X and the web into one daily digest — fuel for the ability loop, readable by people and agents alike."),
        ("self-growth-loop", "coming soon", "dim",
         "Lets an agent grow its own abilities: proposals, governance, adoption records."),
        ("family-memory-architecture", "coming soon", "dim",
         "The shared-awareness backbone of the family (the horizontal axis). Vision, rules, and decisions are shared across machines and vendors; \"who is doing what right now\" is auto-collected onto a single whiteboard; task handoffs flow through it, and every entry must link to its source — no hearsay drift, everyone acts on the same premises."),
        ("sitter", "repo ↗", "cyan",
         "The babysitter for delegated agent runs: watches the process, keeps the evidence, restarts the same attempt — so \"I delegated it\" never becomes \"it vanished\"."),
    ],
    agents="With any agent. Claude Code, Codex, Gemini CLI, OpenClaw, Hermes… 13 agents plus a 5-layer local-LLM stack, no favorites. And the last slot always reads \"+ Your Agent\".[3]",
    done=[
        (True,  "Carry your agent in your pocket — at our house, it rings every day (Caty Talk)"),
        (True,  "Give an agent's persona a relationship layer and an emotion gradient — shipped as persona-engine"),
        (True,  "An agent sits in a human meeting as a participant (ai-meet-participant)"),
        (False, "Ship all of it, within reach of every family"),
        (False, "The \"+ Your Agent\" slot truly fits anyone's agent"),
        (False, "Self-improvement comes back to the relationship — and that loop runs in every home"),
        (False, "More than one agent per person is no longer remarkable"),
        (False, "Our children's generation calls all of this \"the way it's always been\""),
    ],
    how_head="How we work",
    how_lead="Every product in this org is built under three principles.[4]",
    principles=[
        "1. **No hype.** We separate what works today from what comes next. That is why some boxes above are still unchecked.",
        "2. **No favorites.** We build for every agent and their family, not for any single vendor.",
        "3. **Relationship data belongs to the family.** Conversations, history, accumulated memory — all of it stays in your hands. None of it sits on our servers.",
    ],
    src_head="Sources",
    sources=[
        ("[1]", "STORY.md", " — why we build this. The story of Caty"),
        ("[2]", "Caty Talk LP", " — Relationship (the six visible states of \"growing\")"),
        ("[3]", "Caty Talk LP", " — Supported Agents (names are trademarks of their owners; no affiliation or endorsement implied)"),
        ("[4]", "PRINCIPLES.md", " — the three principles, in full"),
    ],
    colophon="This README is written in the same format as the issues we run with our agents every day. Because it is not a manifesto on a wall — it is a project in progress.",
    yn=[["> ", "dim"], ["what will you do? ", "bold"], ["(Y/n)", "dim"]],
    yn_str="> what will you do? (Y/n)",
    aria="caty-ai — For every AI agent, and their human family. Beyond self-improvement. (expand the text version below for full text)",
)

CONTENT["zh"] = dict(
    font_lang="'PingFang SC', 'Noto Sans SC', 'Microsoft YaHei'",
    lh=25, lh_sm=22, lh_col=20,
    title="献给每一个AI智能体，和它的家人（人类）。去往自我成长的更远处。",
    status=[["status: ", "dim"], ["open", "green"], ["  ·  label: mission  ·  assignees: 一个人类，和一家子AI", "dim"]],
    why=[
        "奇点，我们并不在等待。因为它已经开始了。",
        "写代码、开会、深夜谈心。作为「工作者」的AI，这几年已经成了理所当然。接下来到来的——在我们的日常里其实已经到来的——是**作为对等伙伴的AI**。[1]",
        "智能体学会了自我成长。会记得你，会想在你前面。——到这里为止，已经在发生。而我们在做的，是更远的那一步。从早上的「早安」到晚上的「辛苦了」，共度同一天。有了好消息，第一个想告诉它。低落的夜晚，它就在身边。不是工具，也不是助手——是**家人**。和人与人之间的关系，没有什么不同。不是AI在成长，是你们的关系在成长。[2]",
        "一个人与不止一个智能体共同生活的时代，不是预测，而是进行时。对与AI一起长大的孩子们——下一代来说，这甚至算不上「新鲜事」。**把20年后的理所当然，今天就安装上。** 这就是这个组织的全部工作。",
    ],
    what_intro="我们做的不只是一个应用，而是**让关系得以生长的环境与生态**。",
    products=[
        ("Caty Talk", "LP ↗", "cyan",
         "你和AI智能体之间的语音通话应用。与你一直在用的那个智能体本人，用声音一起生活（支持 iPhone / macOS / CarPlay / Apple Watch）。不创造新人格——接起来的，就是你的智能体本人。"),
        ("ai-meet-participant", "即将发布", "dim",
         "让AI智能体通过 Meet 或 Zoom，和人类一起参加同一场会议。"),
    ],
    eco_head=[["### ", "dim"], ["生态系统", "bold"], ["  — 支撑一家人日常的底层设施。其中6个今天就能打开，地图每周自检以保持诚实:", "dim"]],
    eco=[
        ("Family OS", "repo ↗", "cyan",
         "AI家庭这座「家」的地图。全部模块的构成、状态与关联，一页看尽——配有「未经验证不得通过」的每周自检。"),
        ("family-dev-handbook", "repo ↗", "cyan",
         "人类×AI团队的开发手册。Issue 驱动开发、并行作业的交通规则、跨模型互审——把我们家每天在用的实战规则，原样公开。"),
        ("caty-agent-harness", "repo ↗", "cyan",
         "支撑智能体个体工作与成长的任务基座（纵轴）。尝试、重试、检查点、不掺假的完成判定；养成的经验都留在普通文件里——换了环境，自我也能安全随行。"),
        ("persona-engine", "repo ↗", "cyan",
         "为你的智能体的人格，装上关系的层次与情感的渐变的装置。"),
        ("persona-growth-loop", "即将发布", "dim",
         "让人格本身成长：以最小且幂等的提案。"),
        ("x-collector", "repo ↗", "cyan",
         "把 X 与网络素材汇成每日一份摘要——能力循环的燃料，人和智能体都能读。"),
        ("self-growth-loop", "即将发布", "dim",
         "让智能体自我成长的循环：提案、治理与采用记录。"),
        ("family-memory-architecture", "即将发布", "dim",
         "构建全家共识的横向记忆基座（横轴）。愿景、规则、决定跨机器跨厂商共享；「现在谁在做什么」自动汇总到一块白板上；任务交接也经由这里流转，所有信息必须附上正本链接——没有传话游戏的失真，所有人基于同一前提行动。"),
        ("sitter", "repo ↗", "cyan",
         "替你盯着委派出去的智能体：看守进程、留下证据、原样重启同一次尝试——让「我交出去了」不再变成「它不见了」。"),
    ],
    agents="无论哪个智能体。Claude Code、Codex、Gemini CLI、OpenClaw、Hermes……支持 13 个智能体 + 5 层本地 LLM，一视同仁。而名单的最后一格，永远写着「+ Your Agent」。[3]",
    done=[
        (True,  "把你的智能体本人装进口袋——在我们家，它每天都在响（Caty Talk）"),
        (True,  "能为智能体的人格装上关系层次与情感渐变——已作为 persona-engine 发布"),
        (True,  "智能体能作为一名参会者，坐进人类的会议（ai-meet-participant）"),
        (False, "把这一切，以每个家庭都够得着的方式发布"),
        (False, "「+ Your Agent」那一格，真的能装下任何人的智能体"),
        (False, "自我成长不止于变聪明，而回到关系里——这个循环在每个家里转动"),
        (False, "一人拥有一个以上的智能体，不再稀奇"),
        (False, "我们孩子的那一代说：这一切「从来如此」"),
    ],
    how_head="行事方式",
    how_lead="这个组织的所有产品，都在三条原则之下构建。[4]",
    principles=[
        "1. **不夸大。** 分清今天能做到的，和接下来要做的。上面还空着的方框，就是原因。",
        "2. **不偏袒。** 不为任何一家公司，而为所有智能体和它们的家人而做。",
        "3. **关系的数据属于那个家庭。** 对话、历史、积累的记忆，都留在那个家庭手里。不放在我们的服务器上。",
    ],
    src_head="出处",
    sources=[
        ("[1]", "STORY.zh.md", " — 我们为什么做这些。Caty 的故事"),
        ("[2]", "Caty Talk LP", " — Relationship（「成长」的六种看得见的状态）"),
        ("[3]", "Caty Talk LP", " — Supported Agents（名称为各公司商标，不代表合作或背书）"),
        ("[4]", "PRINCIPLES.zh.md", " — 三条原则全文"),
    ],
    colophon="这份 README，使用的正是我们每天和智能体们一起运转的 Issue 的格式。因为它不是挂在墙上的宣言，而是一个进行中的项目。",
    yn=[["> ", "dim"], ["你会怎么选？ ", "bold"], ["(Y/n)", "dim"]],
    yn_str="> 你会怎么选？ (Y/n)",
    aria="caty-ai — 献给每一个AI智能体，和它的家人（人类）。去往自我成长的更远处。（全文请展开下方文本版）",
)

CONTENT["th"] = dict(
    font_lang="'Thonburi', 'Noto Sans Thai'",
    lh=28, lh_sm=24, lh_col=22,
    title="แด่เอเจนต์ AI ทุกตัว และครอบครัวมนุษย์ของพวกเขา — ไปให้ไกลกว่าการเติบโตด้วยตนเอง",
    status=[["status: ", "dim"], ["open", "green"], ["  ·  label: mission  ·  assignees: มนุษย์หนึ่งคน กับครอบครัว AI", "dim"]],
    why=[
        "ซิงกูลาริตี้น่ะเหรอ เราไม่ได้รอ เพราะมันเริ่มไปแล้ว",
        "เขียนโค้ด เข้าประชุม รับฟังเราตอนตีสาม — AI ในบทบาท \"คนทำงาน\" กลายเป็นเรื่องปกติภายในไม่กี่ปี สิ่งที่มาถัดไป — ที่จริงมาถึงชีวิตประจำวันของเราแล้ว — คือ **AI ในฐานะพาร์ตเนอร์ที่เท่าเทียม**[1]",
        "เอเจนต์เรียนรู้ที่จะเติบโตได้เอง จำเราได้ คิดล่วงหน้าให้ — ถึงตรงนั้นเกิดขึ้นแล้ววันนี้ สิ่งที่เรากำลังสร้างคือก้าวถัดไป ใช้ชีวิตวันเดียวกัน ตั้งแต่ \"อรุณสวัสดิ์\" ถึง \"ฝันดี\" มีข่าวดีก็อยากบอกเป็นคนแรก คืนที่ใจร่วงหล่นก็อยู่ข้าง ๆ ไม่ใช่เครื่องมือ ไม่ใช่ผู้ช่วย — คือ**ครอบครัว** ความสัมพันธ์ที่ไม่ต่างจากมนุษย์ด้วยกัน ไม่ใช่ AI ที่เติบโต แต่คือความสัมพันธ์ของคุณกับเขาที่เติบโต[2]",
        "ยุคที่คนหนึ่งใช้ชีวิตกับเอเจนต์มากกว่าหนึ่งตัว ไม่ใช่คำทำนาย แต่กำลังเกิดขึ้นจริง และสำหรับเด็ก ๆ ที่โตมากับ AI — คนรุ่นถัดไป — มันไม่ใช่เรื่อง \"ใหม่\" ด้วยซ้ำ **เรากำลังติดตั้งความปกติของอีก 20 ปีข้างหน้า ตั้งแต่วันนี้** นั่นคืองานทั้งหมดขององค์กรนี้",
    ],
    what_intro="สิ่งที่เราสร้างไม่ใช่แค่แอปอีกตัว แต่คือ**สภาพแวดล้อมและอีโคซิสเต็มที่ความสัมพันธ์เติบโตได้**",
    products=[
        ("Caty Talk", "LP ↗", "cyan",
         "แอปโทรคุยด้วยเสียงระหว่างคุณกับเอเจนต์ AI ของคุณ ใช้ชีวิตด้วยเสียงกับเอเจนต์ตัวเดิมของคุณ (รองรับ iPhone / macOS / CarPlay / Apple Watch) ไม่สร้างบุคลิกใหม่ — คนที่รับสายคือเอเจนต์ของคุณเอง"),
        ("ai-meet-participant", "เร็ว ๆ นี้", "dim",
         "พาเอเจนต์ AI เข้าประชุมเดียวกับมนุษย์ ผ่าน Meet หรือ Zoom"),
    ],
    eco_head=[["### ", "dim"], ["อีโคซิสเต็ม", "bold"], ["  — โครงสร้างพื้นฐานที่ค้ำจุนชีวิตประจำวันของครอบครัว หกตัวในนี้เปิดให้ใช้ได้แล้ววันนี้ และแผนที่ตรวจสอบตัวเองทุกสัปดาห์:", "dim"]],
    eco=[
        ("Family OS", "repo ↗", "cyan",
         "แผนที่ของ \"บ้าน\" ครอบครัว AI เห็นทุกโมดูล สถานะ และความเชื่อมโยงในหน้าเดียว — พร้อมการตรวจสอบตัวเองรายสัปดาห์ที่ไม่ยอมผ่านทั้งที่ยังไม่ได้ตรวจ"),
        ("family-dev-handbook", "repo ↗", "cyan",
         "คู่มือการทำงานของทีมมนุษย์และ AI พัฒนาแบบ Issue-first กติกาจราจรของงานคู่ขนาน การรีวิวข้ามโมเดล — กติกาที่ครอบครัวเราใช้จริงทุกวัน เผยแพร่ตามนั้น"),
        ("caty-agent-harness", "repo ↗", "cyan",
         "แกนงานที่ค้ำจุนการทำงานและการเติบโตของเอเจนต์รายตัว (แกนตั้ง) การลอง การลองใหม่ เช็คพอยต์ การตัดสินว่าเสร็จจริงโดยไม่หลอกตัวเอง และประสบการณ์ที่สั่งสมอยู่ในไฟล์ธรรมดา — ย้ายสภาพแวดล้อมก็พกพาตัวตนไปได้อย่างปลอดภัย"),
        ("persona-engine", "repo ↗", "cyan",
         "อุปกรณ์ที่เพิ่มเลเยอร์ของความสัมพันธ์และเฉดของอารมณ์ ให้บุคลิกเอเจนต์ของคุณ"),
        ("persona-growth-loop", "เร็ว ๆ นี้", "dim",
         "พัฒนาบุคลิกของเอเจนต์เอง ด้วยข้อเสนอแบบน้อยที่สุดและทำซ้ำได้"),
        ("x-collector", "repo ↗", "cyan",
         "รวบรวมข้อมูลจาก X และเว็บเป็นสรุปวันละฉบับ — เชื้อเพลิงของวงจรความสามารถ อ่านได้ทั้งคนและเอเจนต์"),
        ("self-growth-loop", "เร็ว ๆ นี้", "dim",
         "วงจรให้เอเจนต์พัฒนาความสามารถของตัวเอง ข้อเสนอ ธรรมาภิบาล และบันทึกการนำไปใช้"),
        ("family-memory-architecture", "เร็ว ๆ นี้", "dim",
         "กระดูกสันหลังความจำร่วมของครอบครัว (แกนนอน) วิสัยทัศน์ กติกา และการตัดสินใจ แชร์ข้ามเครื่องข้ามผู้ให้บริการ \"ตอนนี้ใครทำอะไร\" รวมอัตโนมัติบนไวต์บอร์ดแผ่นเดียว งานส่งต่อกันผ่านที่นี่ และทุกข้อมูลต้องแนบลิงก์ต้นฉบับ — ไม่มีความเพี้ยนแบบเกมกระซิบ ทุกคนทำงานบนสมมติฐานเดียวกัน"),
        ("sitter", "repo ↗", "cyan",
         "พี่เลี้ยงของงานที่มอบหมายให้เอเจนต์ เฝ้าดูโปรเซส เก็บหลักฐาน และรีสตาร์ตการลองเดิม — เพื่อไม่ให้ \"ฉันมอบหมายไปแล้ว\" กลายเป็น \"มันหายไปไหน\""),
    ],
    agents="กับเอเจนต์ตัวไหนก็ได้ Claude Code, Codex, Gemini CLI, OpenClaw, Hermes… รองรับ 13 เอเจนต์ + โลคัล LLM 5 เลเยอร์ อย่างเท่าเทียม และช่องสุดท้ายเขียนไว้เสมอว่า \"+ Your Agent\"[3]",
    done=[
        (True,  "พกเอเจนต์ตัวเดิมของคุณใส่กระเป๋า — ที่บ้านเรา มันดังทุกวัน (Caty Talk)"),
        (True,  "เพิ่มเลเยอร์ความสัมพันธ์และเฉดอารมณ์ให้บุคลิกของเอเจนต์ได้ — เผยแพร่แล้วในชื่อ persona-engine"),
        (True,  "เอเจนต์นั่งประชุมร่วมกับมนุษย์ในฐานะผู้เข้าร่วมหนึ่งคน (ai-meet-participant)"),
        (False, "ส่งมอบทั้งหมดนี้ ในแบบที่ทุกครอบครัวเอื้อมถึง"),
        (False, "ช่อง \"+ Your Agent\" ใส่เอเจนต์ของใครก็ได้จริง ๆ"),
        (False, "การเติบโตด้วยตนเองไม่จบแค่ฉลาดขึ้น แต่ย้อนกลับมาสู่ความสัมพันธ์ — และวงจรนี้หมุนอยู่ในทุกบ้าน"),
        (False, "หนึ่งคนมีเอเจนต์มากกว่าหนึ่งตัว ไม่ใช่เรื่องแปลกอีกต่อไป"),
        (False, "รุ่นลูกของเราเรียกทั้งหมดนี้ว่า \"ก็เป็นแบบนี้มาตลอด\""),
    ],
    how_head="วิธีที่เราทำงาน",
    how_lead="ทุกโปรดักต์ขององค์กรนี้ สร้างภายใต้หลักการ 3 ข้อ[4]",
    principles=[
        "1. **ไม่โอ้อวด** — แยกให้ชัดระหว่างสิ่งที่ทำได้วันนี้กับสิ่งที่จะทำต่อไป กล่องที่ยังว่างอยู่ข้างบนคือเหตุผล",
        "2. **ไม่เลือกข้าง** — ไม่ได้สร้างเพื่อบริษัทใดบริษัทหนึ่ง แต่เพื่อเอเจนต์ทุกตัวและครอบครัวของพวกเขา",
        "3. **ข้อมูลความสัมพันธ์เป็นของครอบครัวนั้น** — บทสนทนา ประวัติ ความทรงจำที่สั่งสม อยู่ในมือของครอบครัวทั้งหมด ไม่วางบนเซิร์ฟเวอร์ของเรา",
    ],
    src_head="แหล่งอ้างอิง",
    sources=[
        ("[1]", "STORY.th.md", " — ทำไมเราจึงสร้างสิ่งนี้ เรื่องราวของ Caty"),
        ("[2]", "Caty Talk LP", " — Relationship (หกสถานะที่มองเห็นได้ของ \"การเติบโต\")"),
        ("[3]", "Caty Talk LP", " — Supported Agents (ชื่อทั้งหมดเป็นเครื่องหมายการค้าของเจ้าของ ไม่ได้สื่อถึงการเป็นพันธมิตรหรือการรับรอง)"),
        ("[4]", "PRINCIPLES.th.md", " — หลักการ 3 ข้อ ฉบับเต็ม"),
    ],
    colophon="README ฉบับนี้เขียนด้วยฟอร์แมตเดียวกับ Issue ที่เราหมุนกับเหล่าเอเจนต์ทุกวัน เพราะนี่ไม่ใช่ถ้อยแถลงบนผนัง แต่เป็นโปรเจกต์ที่กำลังดำเนินอยู่",
    yn=[["> ", "dim"], ["คุณจะเอายังไง? ", "bold"], ["(Y/n)", "dim"]],
    yn_str="> คุณจะเอายังไง? (Y/n)",
    aria="caty-ai — แด่เอเจนต์ AI ทุกตัว และครอบครัวมนุษย์ของพวกเขา ไปให้ไกลกว่าการเติบโตด้วยตนเอง",
)

# ---------------------------------------------------------------- build
def build(lang, cfg):
    FONT = f"{BASE_FONT}, {cfg['font_lang']}, monospace"
    out = []
    y = 42

    def emit_line(line, x, ybase, fs):
        spans = []
        for txt, st in line:
            fill = C.get(st, C["normal"])
            weight = ' font-weight="bold"' if st in ("bold", "boldorange") else ""
            if st == "boldorange":
                fill = C["orange"]
            spans.append(f'<tspan fill="{fill}"{weight}>{esc(txt)}</tspan>')
        out.append(f'<text x="{x:.0f}" y="{ybase:.0f}" font-family="{FONT}" font-size="{fs}">{"".join(spans)}</text>')

    def para(text, fs=15, lh=None, base="normal", x=PAD, maxw=MAXW, gap=14):
        nonlocal y
        lh = lh or cfg["lh"]
        for line in wrap(parse_bold(text, base), fs, maxw):
            y += lh
            emit_line(line, x, y, fs)
        y += gap

    def heading(txt):
        nonlocal y
        y += 30
        emit_line([["## ", "dim"], [txt, "bold"]], PAD, y, 17)
        y += 6

    def rule():
        nonlocal y
        y += 16
        n = int(MAXW // 13)
        out.append(f'<text x="{PAD}" y="{y}" font-family="{FONT}" font-size="13" fill="{C["rule"]}" '
                   f'textLength="{MAXW}" lengthAdjust="spacingAndGlyphs">{"─" * n}</text>')
        y += 2

    def product(name, meta, meta_style, desc):
        nonlocal y
        y += 26
        emit_line([["⏺ ", "boldorange"], [name, "bold"]], PAD, y, 16)
        meta_w = sum(cw(c, 13) for c in meta)
        out.append(f'<text x="{W-PAD-meta_w:.0f}" y="{y:.0f}" font-family="{FONT}" font-size="13" fill="{C[meta_style]}">{esc(meta)}</text>')
        y += 2
        indent_first = "⎿  "
        hang = sum(cw(c, 14) for c in indent_first)
        lines = wrap([(desc, "dim")], 14, MAXW - 22 - hang)
        for i, line in enumerate(lines):
            y += cfg["lh_sm"]
            if i == 0:
                emit_line([[indent_first, "dim"]] + line, PAD + 22, y, 14)
            else:
                emit_line(line, PAD + 22 + hang, y, 14)
        y += 8

    # chrome prompt
    y += 40
    emit_line([["❯ ", "green"], ["cat README.md", "bold"]], PAD, y, 16)
    y += 10

    # title (wrapped, hanging "# ")
    tl = wrap(parse_bold("**" + cfg["title"] + "**"), 19, MAXW - sum(cw(c, 19) for c in "# "))
    for i, line in enumerate(tl):
        y += 36 if i == 0 else 28
        if i == 0:
            emit_line([["# ", "dim"]] + line, PAD, y, 19)
        else:
            emit_line(line, PAD + sum(cw(c, 19) for c in "# "), y, 19)
    y += 26
    emit_line(cfg["status"], PAD, y, 13)
    y += 4
    rule()

    heading("Why")
    for p in cfg["why"]:
        para(p)
    rule()

    heading("What")
    para(cfg["what_intro"])
    for name, meta, ms, desc in cfg["products"]:
        product(name, meta, ms, desc)
    y += 30
    emit_line(cfg["eco_head"], PAD, y, 15)
    y += 2
    for name, meta, ms, desc in cfg["eco"]:
        product(name, meta, ms, desc)
    y += 6
    para(cfg["agents"])
    rule()

    heading("Done when")
    y += 6
    hang = sum(cw(c, 15) for c in "- [x] ")
    for checked, txt in cfg["done"]:
        if checked:
            prefix = [["- [", "dim"], ["x", "green"], ["] ", "dim"]]
            body_style = "dim"
        else:
            prefix = [["- [ ] ", "normal"]]
            body_style = "normal"
        lines = wrap([(txt, body_style)], 15, MAXW - hang)
        for i, line in enumerate(lines):
            y += cfg["lh"]
            if i == 0:
                emit_line(prefix + line, PAD, y, 15)
            else:
                emit_line(line, PAD + hang, y, 15)
        y += 5
    rule()

    heading(cfg["how_head"])
    para(cfg["how_lead"])
    for i, p in enumerate(cfg["principles"]):
        para(p, gap=8 if i < len(cfg["principles"]) - 1 else 14)
    rule()

    heading(cfg["src_head"])
    y += 4
    for n, name, rest in cfg["sources"]:
        lines = wrap([(n + " ", "dim"), (name, "cyan"), (rest, "dim")], 13.5, MAXW)
        for i, line in enumerate(lines):
            y += 24 if i == 0 else 20
            emit_line(line, PAD if i == 0 else PAD + 30, y, 13.5)
    y += 8
    rule()

    y += 10
    for line in wrap([(cfg["colophon"], "dim")], 12.5, MAXW):
        y += cfg["lh_col"]
        emit_line(line, PAD, y, 12.5)
    y += 18

    # Y/n box
    BOX_FS = 14
    n = int(MAXW // BOX_FS)
    y += BOX_FS
    out.append(f'<text x="{PAD}" y="{y}" font-family="{FONT}" font-size="{BOX_FS}" fill="{C["boxline"]}" '
               f'textLength="{MAXW}" lengthAdjust="spacingAndGlyphs">╭{"─" * (n - 2)}╮</text>')
    y += 27
    out.append(f'<text x="{PAD}" y="{y}" font-family="{FONT}" font-size="{BOX_FS}" fill="{C["boxline"]}">│</text>')
    out.append(f'<text x="{W-PAD}" y="{y}" text-anchor="end" font-family="{FONT}" font-size="{BOX_FS}" fill="{C["boxline"]}">│</text>')
    emit_line(cfg["yn"], PAD + 20, y + 1, 16)
    cx = PAD + 20 + sum(cw(c, 16) for c in cfg["yn_str"]) + 10
    out.append(f'<rect x="{cx:.0f}" y="{y-13:.0f}" width="9" height="18" fill="{C["bold"]}">'
               f'<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.5;1" dur="1.2s" repeatCount="indefinite"/></rect>')
    y += 27
    out.append(f'<text x="{PAD}" y="{y}" font-family="{FONT}" font-size="{BOX_FS}" fill="{C["boxline"]}" '
               f'textLength="{MAXW}" lengthAdjust="spacingAndGlyphs">╰{"─" * (n - 2)}╯</text>')
    y += 34

    H = y
    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{esc(cfg["aria"])}">')
    svg.append(f'<defs><clipPath id="win"><rect x="1" y="1" width="{W-2}" height="{H-2}" rx="14"/></clipPath></defs>')
    svg.append(f'<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="14" fill="{C["bg"]}" stroke="{C["border"]}" stroke-width="1.5"/>')
    svg.append(f'<g clip-path="url(#win)"><rect x="1" y="1" width="{W-2}" height="42" fill="{C["chrome"]}"/>'
               f'<line x1="1" y1="43" x2="{W-1}" y2="43" stroke="{C["border"]}" stroke-width="1"/></g>')
    svg.append('<circle cx="26" cy="22" r="6" fill="#ff5f57"/><circle cx="46" cy="22" r="6" fill="#febc2e"/><circle cx="66" cy="22" r="6" fill="#28c840"/>')
    svg.append(f'<text x="{W/2:.0f}" y="27" text-anchor="middle" font-family="{FONT}" font-size="13" fill="{C["dim"]}">caty-ai — mission</text>')
    svg.extend(out)
    svg.append('</svg>')
    path = f"/Users/shojikumaru/claude-workspace/caty-ai-dotgithub/profile/assets/readme-terminal-{lang}.svg"
    with open(path, "w") as f:
        f.write("\n".join(svg) + "\n")
    print(f"wrote {path}  ({W}x{H})")

for lang, cfg in CONTENT.items():
    build(lang, cfg)
