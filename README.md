# github-issues-calendar
## 概要
Githubのissueの更新日を取得して、ブラウザ上のカレンダーでissueの一覧を表示するツールです

## 動作確認環境
- OS : windows
- 使用の前提 : Docker Desktopのインストール・ログイン・起動中であること

## セットアップ
- git clone https://github.com/toigni/github-issues-calendar.git
- cd github-issues-calendar
- .envファイルに以下を設定
    - GITHUB_TOKEN=GithubのToken
    - REPO=ユーザー名/リポジトリ名
    - CACHE_TTL=キャッシュを取得するタイミング、デフォルトは3600秒(1時間)
- docker compose build 

## 起動方法
- docker compose up