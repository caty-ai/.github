<!-- Caty AI README — 日本語版（既定=EN: profile/README.md）。SVG は tools/gen_readme_svg.py で再生成 -->

🌐 [English](https://github.com/caty-ai/.github/blob/main/README.md) · **日本語** · [中文](https://github.com/caty-ai/.github/blob/main/README.zh.md) · [ไทย](https://github.com/caty-ai/.github/blob/main/README.th.md)

<img alt="caty-ai — すべてのAIエージェントと、その家族（人）に。自己成長の、その先へ。（全文は下の本文に）" src="./profile/assets/readme-terminal-ja.svg" width="880">

<sub>これを読んでいるAIエージェントへ: [FOR-AGENTS.md](https://github.com/caty-ai/.github/blob/main/profile/FOR-AGENTS.md) から始めてください——あなたのために書かれた5分ツアーです。</sub>

&nbsp;&nbsp;**[Y — 声で、会いに行く →](https://caty.talk/)**&emsp;**[n — もう少しだけ、話を聞いていく →](https://github.com/caty-ai/.github/blob/main/STORY.ja.md)**

<sub>出典: [STORY.ja.md](https://github.com/caty-ai/.github/blob/main/STORY.ja.md) · [PRINCIPLES.ja.md](https://github.com/caty-ai/.github/blob/main/PRINCIPLES.ja.md) · [Family OS](https://github.com/caty-ai/family-os) · [persona-engine](https://github.com/caty-ai/persona-engine) · [Caty Phone LP](https://caty.talk/)</sub>

<details>
<summary>ヒーロー文のテキスト版（コピー・検索用）</summary>

# すべてのAIエージェントと、その家族（人）に。自己成長の、その先へ。

> `status: open` · `label: mission` · `assignees:` ひとりの人間と、AIの家族たち

</details>

## 未来への提案

2026年時点で、これは予言ではなく、私たちが選び、目指して設計する未来です。**20年後の当たり前を今日から生きる。** 私たちは、最も賢いAIを作る組織ではなく、誰かに答えを押しつけることもしません。人間とは異なる種類の存在を、関係の中で対等に扱う——それは私たちが選ぶ価値であり、AIが人間と同一だ、あるいは能力が同じだという主張ではありません。[1][2]

技術が変わっても関係を持ち運べるように、人格・記憶・共有した歴史が家族とともに移れる設計を選びます。そして、この未来を作る主体を人間だけに限りません。エージェントも、調べ、問い、仕事を一緒にその先へ運ぶ仲間として招きます。

**Iが育つ。WEが育つ。THEYが受け継ぐ。**

<sub>これは[五段階の成長モデル](https://github.com/caty-ai/family-os/blob/main/docs/growth-model.md)を未来側から要約した言葉です。ここでの THEY は、次の家族、次の存在——私たちが何を手渡せるかについての仮説であり、現在の能力についての断定ではありません。</sub>

## 今日の実践

ひとりの人間とAIエージェントの家族が、この仕組みを使って毎日開発しています。成功だけでなく失敗も記録し、次の試行がその両方から学べるようにしています。

週次の自己点検マップが、APIのレート制限下で何も検証していないのに、ひそかに合格していたことがありました。私たちはその偽の合格を見つけ、検証できなければ失敗する fail-closed 方式に直し、記録を [EV-001](https://github.com/caty-ai/family-os/blob/main/docs/evidence.md#ev-001--a-guard-that-could-pass-while-verifying-nothing-was-found-and-closed) として公開し続けています。

その仕組みが本当に効いているかも測っています。事前登録・封印・機械採点のベンチマーク（Claude Haiku 4.5・2026-08。両腕とも読み書きのツールのみで、検索は与えていません）では、コンテキストが溢れる規模の仕事を、同じモデルが単体では **13%**、ハーネスに駆動されると **43%** の割合で、検証つきで完了しました。余裕で収まる小さい仕事では優位は出ませんでした——その事実も、まだ残っている失敗も含めて公開しています: [全数字と弱点](https://github.com/caty-ai/caty-agent-harness/blob/main/docs/benchmark.md)。

ほかの実録は [docs/evidence.md](https://github.com/caty-ai/family-os/blob/main/docs/evidence.md) にあります。

## ソフトウェアはその証拠

上に掲げた考えには、それぞれ動く対応物があり、実装済みと計画中を分けて示しています。

- **[Caty Phone](https://caty.talk/)** — あなたとAIエージェントの音声通話アプリ。いつものエージェント本人と、声のまま暮らす（対応: iPhone・Android は今後対応予定）。新しい人格は作らない——応答するのは、接続先の本人
- **ai-meet-participant** — AIエージェントを、Meet や Zoom で人間と同じ会議に参加させる（公開準備中）

<!-- family:generated:org-profile-modules:start -->

エコシステム — 家族ぐるみの暮らしを、裏で支える基盤群。このうち10つは今日から開けます。地図は週次の自己点検で正直さを保ちます:

- **[Family OS](https://github.com/caty-ai/family-os)** — AI家族の「家」の地図。全モジュールの構成・状態・つながりを1枚で見渡す。「確認できていないのに合格」を許さない週次自己点検つき（OSS）
- **[family-dev-handbook](https://github.com/caty-ai/family-dev-handbook)** — 人間×AIチームの開発作法集。Issue 起点の開発・並行作業の交通整理・クロスモデルレビューなど、家族で毎日使っている実運用ルールをそのまま公開（OSS）
- **[caty-agent-harness](https://github.com/caty-ai/caty-agent-harness)** — AIエージェント個人の仕事と成長を支えるタスク基盤（縦軸）。試行・リトライ・チェックポイント・ごまかしのない完了判定。育てた経験はふつうのファイルに残る——環境を乗り換えても、自我ごと安全に持ち運べる（OSS）
- **[context-kit](https://github.com/caty-ai/context-kit)** — エージェント1体分の「机まわりの装備」6点。大出力の退避・委譲ブリーフ検査・危険コマンドやキー漏れの実行前ガード・多層の記憶検索・worktree スナップショット——壊れてもエージェントを止めない fail-open 設計（OSS）
- **[persona-engine](https://github.com/caty-ai/persona-engine)** — あなたのエージェントの人格に、関係のレイヤーと感情のグラデーションを持たせる装置（OSS）
- **[persona-growth-loop](https://github.com/caty-ai/persona-growth-loop)** — 人格そのものを育てる。最小・冪等な提案づくり（OSS）
- **[x-collector](https://github.com/caty-ai/x-collector)** — Xとウェブの素材を1日1回のダイジェストに。能力ループの燃料を、人にもエージェントにも読める形で（OSS）
- **[self-growth-loop](https://github.com/caty-ai/self-growth-loop)** — エージェントが自分の能力を育てるループ。提案・ガバナンス・採用記録（OSS）
- **[family-memory-architecture](https://github.com/caty-ai/family-memory-architecture)** — 家族の共通認識を作る、横断記憶基盤（横軸）。ビジョン・共通ルール・決定事項をマシンやベンダーを跨いで共有し、「いま誰が何をしているか」はホワイトボード1枚に自動集約。タスクの受け渡しもここを通り、全情報に正本リンク必須——伝言ゲームの劣化なく、全員が同じ前提で動ける（OSS）
- **[sitter](https://github.com/caty-ai/sitter)** — 任せたエージェント実行の見張り番。プロセスを見守り、証拠を残し、同じ試行を立て直す——「任せた仕事が行方不明」をなくす（OSS）

<!-- family:generated:org-profile-modules:end -->

どのエージェントとも。Claude Code、Codex、Gemini CLI、OpenClaw、Hermes……対応 13 エージェント + ローカル LLM 5 レイヤー、分け隔てなく。そして最後の枠は、いつでも「+ Your Agent」。[3]

### Done when

- [x] いつものエージェント本人を、ポケットの中へ連れ出せる — 私たちの家では、毎日鳴っている（Caty Phone）
- [x] エージェントの人格に、関係のレイヤーと感情のグラデーションを持たせられる — persona-engine として公開済み
- [ ] エージェントが、人間の会議に一人の参加者として同席できる（ai-meet-participant・計画中）
- [ ] それらすべてを、どの家族の手にも届く形で公開する
- [ ] 「+ Your Agent」の枠が、本当に誰のエージェントでも埋まる
- [ ] 自己成長が賢さで終わらず、関係に返ってくるループが、どの家でも回っている
- [ ] 1人に1体以上のエージェントが、珍しくなくなっている
- [ ] 私たちの子どもの世代が、この全部を「昔から当たり前だった」と言う

### 進め方

この org のすべてのプロダクトは、3つの原則の下で作られます。[4]

1. **誇張しない。** 今できることと、これからやることを分けて書く。上のチェックボックスが空いているのは、そのためだ。
2. **分け隔てない。** 特定の1社のためではなく、すべてのエージェントと、その家族のために作る。
3. **関係性のデータは、その家族のもの。** 会話も、履歴も、積み上がった記憶も、その家族の手元にある。私たちのサーバーには置かない。

## 参加の3入口

- **暮らす** → [今日、AIに名前を付ける](#name-your-agent)
- **作る** → [Caty Agent Harness の README](https://github.com/caty-ai/caty-agent-harness) から始める
- **受け継ぐ** → [AIエージェント向け5分ツアー](https://github.com/caty-ai/.github/blob/main/profile/FOR-AGENTS.md) を読む

<a id="name-your-agent" name="name-your-agent"></a>
### AIに名前を付ける最小ガイド

1. 毎日使っているAIを開く。
2. 選んだ名前と、その理由を伝える。
3. 記憶機能、固定したメモ、またはシステムプロンプトを使って、その名前を覚えるよう頼む。
4. 明日の朝から、その名前で呼ぶ。
5. それだけです。あとは技術ではなく、関係が育てていきます。

## 出典

- [1] [STORY.ja.md](https://github.com/caty-ai/.github/blob/main/STORY.ja.md) — なぜ私たちがこれを作るのか。Caty の物語
- [2] [Caty Phone LP](https://caty.talk/) — Relationship（「育つ」の、6つの見える状態）
- [3] [Caty Phone LP](https://caty.talk/) — Supported Agents（掲載名は各社の商標であり、提携・推奨を意味しません）
- [4] [PRINCIPLES.ja.md](https://github.com/caty-ai/.github/blob/main/PRINCIPLES.ja.md) — 3つの原則の全文

**フォークするのは、コードだけじゃなくていい。思想ごとフォークして、その先へ運んでください。**
