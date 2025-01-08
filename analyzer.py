import os
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

        token_indicators = {
            'has_token': False,
            'token_info': [],
            'readme_content': readme_content
        }
        
        token_keywords = [
            'token contract', 'ERC20', 'ERC721', 'tokenomics',
            'token address', 'smart contract', 'token sale',
            'ICO', 'IDO', 'token distribution'
        ]
        
        combined_text = (readme_content or '').lower()
        for keyword in token_keywords:
            if keyword in combined_text:
                token_indicators['has_token'] = True
                token_indicators['token_info'].append(keyword)
        
        return token_indicators

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
                    'has_token': repo_details['has_token'],
                    'token_details': repo_details['token_info'],
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
        """より具体的なトレンドを分析して要約を生成"""
        # 詳細な特徴分析
        features = {
            'tool_type': [],      # ツールの種類
            'integrations': [],   # 統合されているサービス/ツール
            'architectures': [],  # アーキテクチャの特徴
            'use_cases': []       # 具体的なユースケース
        }
        
        # 各リポジトリの詳細分析
        for repo in trending_repos:
            desc = (repo['description'] or '').lower()
            readme = repo.get('readme_content', '').lower()
            content = desc + ' ' + readme
            
            # ツールタイプの分析
            if 'code interpreter' in content or 'code generation' in content:
                features['tool_type'].append('コード生成/解釈')
            if 'knowledge retrieval' in content or 'rag' in content:
                features['tool_type'].append('知識検索/RAG')
            
            # 統合の分析
            if 'discord' in content or 'slack' in content:
                features['integrations'].append('チャットツール統合')
            if 'chrome' in content or 'browser' in content:
                features['integrations'].append('ブラウザ統合')
            
            # アーキテクチャの分析
            if 'multi agent' in content or 'multi-agent' in content:
                features['architectures'].append('マルチエージェント')
            if 'plugin' in content or 'extension' in content:
                features['architectures'].append('プラグイン拡張')
            
            # ユースケースの分析
            if 'trading' in content or 'market' in content:
                features['use_cases'].append('取引/市場分析')
            if 'coding assistant' in content or 'development' in content:
                features['use_cases'].append('開発支援')

        # 最も言及の多い特徴を抽出
        trends = []
        for category, items in features.items():
            if items:
                most_common = max(set(items), key=items.count)
                if category == 'tool_type' and items:
                    trends.append(f"{most_common}に特化したツールが注目を集めています")
                elif category == 'integrations' and items:
                    trends.append(f"{most_common}を実装したプロジェクトが増加傾向です")
                elif category == 'architectures' and items:
                    trends.append(f"{most_common}アーキテクチャを採用した実装が主流になっています")
                elif category == 'use_cases' and items:
                    trends.append(f"{most_common}向けの特化型エージェントの開発が活発です")

        # 要約をフォーマット
        summary = f"# AI Agent GitHub Trend Report\n\n"
        summary += f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        summary += "## 本日のトレンド要約\n\n"
        
        # トレンドが見つかった場合のみ表示
        main_points = [t for t in trends if t][:3]
        if main_points:
            for point in main_points:
                summary += f"- {point}\n"
        else:
            summary += "- 本日は特筆すべき新しいトレンドは見られません\n"
        summary += "\n"
        
        return summary
        return summary

    def analyze_repository_content(self, description, readme_content):
        """リポジトリの内容を詳細に分析"""
        content = (description or '').lower() + ' ' + (readme_content or '').lower()
        
        # 主な特徴を抽出
        features = {
            'framework': 'framework' in content or 'library' in content,
            'autonomous': 'autonomous' in content or 'self-operating' in content,
            'assistant': 'assistant' in content or 'chat' in content,
            'multi_agent': 'multi agent' in content or 'multi-agent' in content,
            'llm': 'llm' in content or 'language model' in content or 'gpt' in content,
            'tools': 'tool' in content or 'plugin' in content,
            'rag': 'rag' in content or 'retrieval' in content,
            'web': 'browser' in content or 'web' in content,
            'api': 'api' in content or 'rest' in content
        }
        
        # 技術スタックを抽出
        tech_stack = []
        if 'python' in content: tech_stack.append('Python')
        if 'javascript' in content or 'nodejs' in content: tech_stack.append('JavaScript')
        if 'typescript' in content: tech_stack.append('TypeScript')
        
        # 統合サービスを抽出
        integrations = []
        if 'discord' in content: integrations.append('Discord')
        if 'slack' in content: integrations.append('Slack')
        if 'telegram' in content: integrations.append('Telegram')
        
        # ユースケースを抽出
        use_cases = []
        if 'development' in content or 'coding' in content: use_cases.append('開発支援')
        if 'trading' in content or 'market' in content: use_cases.append('市場分析')
        if 'research' in content or 'academic' in content: use_cases.append('研究支援')
        if 'data analysis' in content or 'analytics' in content: use_cases.append('データ分析')

        return features, tech_stack, integrations, use_cases

    def translate_description(self, description, readme_content=''):
        """説明文を日本語に要約（詳細版）"""
        if not description and not readme_content:
            return "説明なし"
        
        # READMEからプロジェクト名と説明を抽出
        readme_lines = readme_content.split('\n') if readme_content else []
        main_description = ''
        
        # READMEの最初の意味のある行を探す
        for line in readme_lines:
            line = line.strip()
            if line and not line.startswith('#') and not line.startswith('!['):
                main_description = line
                break
        
        # 説明がない場合はdescriptionを使用
        if not main_description:
            main_description = description
            
        # ブロックチェーン/Web3関連キーワード
        blockchain_terms = {
            'on-chain': 'オンチェーン',
            'smart contract': 'スマートコントラクト',
            'validator': 'バリデータ',
            'infrastructure': 'インフラストラクチャ',
            'gateway': 'ゲートウェイ'
        }
        
        # 日本語に翻訳
        translated = main_description.lower()
        for eng, jpn in blockchain_terms.items():
            translated = translated.replace(eng.lower(), jpn)
            
        # 一般的な説明を日本語化
        translated = (
            translated
            .replace('ai-powered', 'AI駆動の')
            .replace('framework', 'フレームワーク')
            .replace('efficient', '効率的な')
            .replace('unified', '統合された')
            .replace('adaptive', '適応型の')
            .replace('automation', '自動化')
            .replace('seamless', 'シームレスな')
            .replace('scalability', 'スケーラビリティ')
            .replace('precision', '高精度')
        )
        
        # 文章を整形
        translated = translated.capitalize()
        if not translated.endswith('.'):
            translated = translated + '。'
            
        return translated

    def save_report(self, trending_repos, filename="ai_agent_trends_report.md"):
        """マークダウンレポートを保存する"""
        if not trending_repos:
            report = "# AI Agent GitHub Trend Report\n\n"
            report += f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            report += "トレンドのあるリポジトリは見つかりませんでした。\n"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(report)
            return

        # 要約を生成
        report = self.analyze_trends(trending_repos)
        
        # 各リポジトリの詳細
        for i, repo in enumerate(trending_repos, 1):
            report += f"## {i}. **[{repo['name']}]({repo['url']})**\n\n"
            report += f"**概要**: {self.translate_description(repo['description'], repo['readme_content'])}\n\n"
            report += f"**統計情報**:\n"
            report += f"- スター数: {repo['stars']} (1日あたり {repo['stars_per_day']})\n"
            report += f"- フォーク数: {repo['forks']} (1日あたり {repo['forks_per_day']})\n"
            report += f"- 作成日: {repo['created_at']}\n"
            
            # 作成者情報
            owner = repo['owner']
            report += f"\n**作成者情報**:\n"
            report += f"- 名前: {owner['name'] or owner['username']}\n"
            if owner['twitter']:
                report += f"- Twitter: [@{owner['twitter']}](https://twitter.com/{owner['twitter']})\n"
            if owner['blog']:
                report += f"- ブログ/サイト: {owner['blog']}\n"

            # トークン情報（存在する場合のみ）
            if repo['has_token']:
                report += f"\n**トークン情報**:\n"
                report += "- トークンの存在が確認されました\n"
                if repo['token_details']:
                    report += "- 関連キーワード: " + ", ".join(repo['token_details']) + "\n"
            report += "\n---\n\n"
            
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