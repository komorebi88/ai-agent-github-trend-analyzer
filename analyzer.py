import os
import re
from datetime import datetime, timedelta
import requests
import time
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

class GitHubTrendAnalyzer:
    def __init__(self):
        self.github_token = os.getenv('GH_PAT')
        if not self.github_token:
            raise ValueError("GitHub token not found. Please check your .env file.")
            
        self.headers = {
            'Authorization': f'token {self.github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        self.base_url = 'https://api.github.com'
        self.search_keywords = [
            'AI agent', 'autonomous agent', 'LLM agent'
        ]

    def check_token(self):
        """トークンの有効性を確認"""
        url = f'{self.base_url}/user'
        response = requests.get(url, headers=self.headers)
        return response.status_code == 200

    def get_repository_details(self, repo_name):
        """リポジトリの詳細情報を取得（READMEを含む）"""
        url = f'{self.base_url}/repos/{repo_name}/readme'
        response = requests.get(url, headers=self.headers)
        readme_content = ''
        if response.status_code == 200:
            import base64
            content = response.json().get('content', '')
            if content:
                readme_content = base64.b64decode(content).decode('utf-8')

        return {
            'readme_content': readme_content
        }

    def get_user_info(self, username):
        """ユーザーの情報を取得（Twitter含む）"""
        url = f'{self.base_url}/users/{username}'
        response = requests.get(url, headers=self.headers)
        if response.status_code != 200:
            return None
        user_data = response.json()
        return {
            'twitter_username': user_data.get('twitter_username'),
            'name': user_data.get('name'),
            'blog': user_data.get('blog')
        }

    def search_repositories(self, keyword, days_ago=7):
        """リポジトリを検索する"""
        date_threshold = (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d')
        query = f'{keyword} created:>{date_threshold}'
        
        url = f'{self.base_url}/search/repositories'
        params = {
            'q': query,
            'sort': 'stars',
            'order': 'desc',
            'per_page': 30
        }
        
        response = requests.get(url, headers=self.headers, params=params)
        if response.status_code != 200:
            print(f"エラー: {response.status_code}")
            return []
            
        return response.json().get('items', [])

    def calculate_growth_metrics(self, repos_data):
        """成長率を計算する"""
        trending_repos = []
        
        for repo in repos_data:
            created_at = datetime.strptime(repo['created_at'], '%Y-%m-%dT%H:%M:%SZ')
            days_since_creation = (datetime.now() - created_at).days or 1
            
            stars_per_day = repo['stargazers_count'] / days_since_creation
            forks_per_day = repo['forks_count'] / days_since_creation
            
            if (stars_per_day >= 50 or forks_per_day >= 10) and days_since_creation <= 30:
                owner_username = repo['owner']['login']
                owner_info = self.get_user_info(owner_username)
                repo_details = self.get_repository_details(repo['full_name'])
                
                trending_repos.append({
                    'name': repo['full_name'],
                    'url': repo['html_url'],
                    'description': repo['description'] or 'No description',
                    'stars': repo['stargazers_count'],
                    'forks': repo['forks_count'],
                    'created_at': created_at.strftime('%Y-%m-%d'),
                    'stars_per_day': round(stars_per_day, 2),
                    'forks_per_day': round(forks_per_day, 2),
                    'readme_content': repo_details['readme_content'],
                    'owner': {
                        'username': owner_username,
                        'twitter': owner_info.get('twitter_username') if owner_info else None,
                        'name': owner_info.get('name') if owner_info else None,
                        'blog': owner_info.get('blog') if owner_info else None
                    }
                })
                
        return sorted(trending_repos, key=lambda x: x['stars_per_day'], reverse=True)

    def analyze_trends(self, trending_repos):
        """トレンドを分析して要約を生成"""
        features = {
            'tool_type': [],      # ツールの種類
            'integrations': [],   # 統合されているサービス/ツール
            'architectures': [],  # アーキテクチャの特徴
            'use_cases': []       # 具体的なユースケース
        }
        
        # 各リポジトリの分析
        for repo in trending_repos:
            desc = (repo['description'] or '').lower()
            readme = repo['readme_content'].lower()
            content = desc + ' ' + readme

            # 分類ロジック
            if 'code' in content or 'coding' in content:
                features['use_cases'].append('開発支援')
            if 'research' in content or 'academic' in content:
                features['use_cases'].append('研究支援')
            if 'chat' in content or 'conversation' in content:
                features['tool_type'].append('対話型AI')
            if 'autonomous' in content:
                features['architectures'].append('自律型')
            if 'multi-agent' in content or 'multi agent' in content:
                features['architectures'].append('マルチエージェント')
            if 'plugin' in content or 'extension' in content:
                features['integrations'].append('プラグイン対応')

        # 特徴の集計と分析
        trend_summary = []
        for category, items in features.items():
            if items:
                unique_items = list(set(items))
                most_common = max(unique_items, key=items.count)
                if len(items) >= 2:  # 十分なデータがある場合のみトレンドとして扱う
                    if category == 'use_cases':
                        trend_summary.append(f"{most_common}に特化したプロジェクトが増加しています")
                    elif category == 'tool_type':
                        trend_summary.append(f"{most_common}の実装が注目されています")
                    elif category == 'architectures':
                        trend_summary.append(f"{most_common}アーキテクチャの採用が進んでいます")
                    elif category == 'integrations':
                        trend_summary.append(f"{most_common}の実装が増えています")

        # トレンドが見つからない場合のデフォルトメッセージ
        if not trend_summary:
            trend_summary = ["現時点で特筆すべきトレンドは見られません"]

        return trend_summary[:3]  # 上位3つのトレンドを返す

    def format_report(self, trending_repos):
        """レポートを整形"""
        report = "# AI Agent GitHub Trend Report\n\n"
        report += f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        report += "## 本日のトレンド要約\n\n"
        
        # トレンド要約を箇条書きで追加
        trend_points = self.analyze_trends(trending_repos)
        for point in trend_points:
            report += f"- {point}\n"
        report += "\n"
        
        # 各リポジトリの詳細
        for i, repo in enumerate(trending_repos, 1):
            report += f"## {i}. **[{repo['name']}]({repo['url']})**\n\n"
            
            # 概要の抽出と翻訳
            description = self.extract_and_translate_description(repo['description'], repo['readme_content'])
            report += f"**概要**:\n{description}\n\n"
            
            report += "**統計情報**:\n"
            report += f"- スター数: {repo['stars']} (1日あたり {repo['stars_per_day']})\n"
            report += f"- フォーク数: {repo['forks']} (1日あたり {repo['forks_per_day']})\n"
            report += f"- 作成日: {repo['created_at']}\n\n"
            
            # 作成者情報
            owner = repo['owner']
            report += "**作成者情報**:\n"
            report += f"- 名前: {owner['name'] or owner['username']}\n"
            if owner['twitter']:
                report += f"- Twitter: [@{owner['twitter']}](https://twitter.com/{owner['twitter']})\n"
            if owner['blog']:
                report += f"- ブログ/サイト: {owner['blog']}\n"
            
            report += "\n---\n\n"
        
        return report

    def extract_and_translate_description(self, description, readme_content):
        """リポジトリの説明を抽出して翻訳"""
        # READMEから主要な説明を抽出
        main_content = ''
        if readme_content:
            lines = [line.strip() for line in readme_content.split('\n')]
            content_lines = []
            
            # 意味のある行を探す
            for line in lines:
                # HTMLタグと特殊な記号を除去
                line = re.sub(r'<[^>]+>', '', line)
                line = re.sub(r'\[.*?\]', '', line)
                line = line.strip()
                
                # 有効な説明文の条件
                if line and not any(x in line.lower() for x in [
                    'readme', 'language', 'english', '中文', '日本語', 'korean',
                    'http', 'github', 'license', '# ', '## ', '### '
                ]):
                    content_lines.append(line)
                    if len(content_lines) == 3:  # 最初の意味のある3行を取得
                        break
            
            main_content = ' '.join(content_lines)
        
        # 説明がない場合はdescriptionを使用
        if not main_content and description:
            main_content = description
        elif not main_content:
            return "説明が提供されていません。"

        # 翻訳辞書
        translation_dict = {
            'ai agent': 'AIエージェント',
            'agent': 'エージェント',
            'artificial intelligence': '人工知能',
            'framework': 'フレームワーク',
            'autonomous': '自律型',
            'research': '研究',
            'workflow': 'ワークフロー',
            'implementation': '実装',
            'development': '開発',
            'experimental': '実験的',
            'repository': 'リポジトリ',
            'resources': 'リソース',
            'collection': 'コレクション',
            'machine learning': '機械学習',
            'language model': '言語モデル',
            'llm': 'LLM',
            'integration': '統合',
            'automation': '自動化',
            'platform': 'プラットフォーム'
        }

        # 翻訳処理
        translated = main_content.lower()
        for eng, jpn in translation_dict.items():
            translated = translated.replace(eng, jpn)

        # 文章を整形
        sentences = re.split(r'[.。]', translated)
        sentences = [s.strip().capitalize() for s in sentences if s.strip()]
        
        # 3行以内に要約
        summary = sentences[:3]
        if summary:
            return '。\n'.join(summary) + '。'
        else:
            return "説明が提供されていません。"

    def save_report(self, trending_repos, filename="ai_agent_trends_report.md"):
        """マークダウンレポートを保存する"""
        report = self.format_report(trending_repos)
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"レポートを {filename} に保存しました。")

    def run_analysis(self):
        """分析を実行する"""
        print("分析を開始します...")
        all_repos = []
        
        for keyword in self.search_keywords:
            print(f"キーワード '{keyword}' で検索中...")
            repos = self.search_repositories(keyword)
            all_repos.extend(repos)
            time.sleep(1)  # API制限を考慮して待機
            
        print("トレンド分析中...")
        unique_repos = {repo['id']: repo for repo in all_repos}.values()
        trending_repos = self.calculate_growth_metrics(unique_repos)
        
        print(f"{len(trending_repos)}件のトレンドリポジトリが見つかりました。")
        self.save_report(trending_repos)
        print("分析が完了しました。")

if __name__ == "__main__":
    try:
        analyzer = GitHubTrendAnalyzer()
        if not analyzer.check_token():
            print("エラー: GitHubトークンが無効です。トークンを確認してください。")
            exit(1)
        print("GitHubトークンの確認が完了しました。")
        analyzer.run_analysis()
    except Exception as e:
        print(f"エラーが発生しました: {e}")