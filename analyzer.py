import os
from datetime import datetime, timedelta
import requests
import time
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

class GitHubTrendAnalyzer:
    def __init__(self):
        self.github_token = os.getenv('GITHUB_TOKEN')
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
        # READMEを取得
        url = f'{self.base_url}/repos/{repo_name}/readme'
        response = requests.get(url, headers=self.headers)
        readme_content = ''
        if response.status_code == 200:
            import base64
            content = response.json().get('content', '')
            if content:
                readme_content = base64.b64decode(content).decode('utf-8')

        # トークン関連情報を確認
        token_indicators = {
            'has_token': False,
            'token_info': []
        }
        
        # トークン関連のキーワード
        token_keywords = [
            'token contract', 'ERC20', 'ERC721', 'tokenomics',
            'token address', 'smart contract', 'token sale',
            'ICO', 'IDO', 'token distribution'
        ]
        
        # 説明文とREADMEでトークン関連キーワードを検索
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
            'per_page': 30  # 取得数を制限して処理を軽くする
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
                # Get owner information
                owner_username = repo['owner']['login']
                owner_info = self.get_user_info(owner_username)
                
                # Get token information
                repo_details = self.get_repository_details(repo['full_name'])
                token_info = repo_details if repo_details else {'has_token': False, 'token_info': []}

                trending_repos.append({
                    'name': repo['full_name'],
                    'url': repo['html_url'],
                    'description': repo['description'] or 'No description',
                    'stars': repo['stargazers_count'],
                    'forks': repo['forks_count'],
                    'created_at': created_at.strftime('%Y-%m-%d'),
                    'stars_per_day': round(stars_per_day, 2),
                    'forks_per_day': round(forks_per_day, 2),
                    'has_token': token_info['has_token'],
                    'token_details': token_info['token_info'],
                    'owner': {
                        'username': owner_username,
                        'twitter': owner_info.get('twitter_username') if owner_info else None,
                        'name': owner_info.get('name') if owner_info else None,
                        'blog': owner_info.get('blog') if owner_info else None
                    }
                })
                
        return sorted(trending_repos, key=lambda x: x['stars_per_day'], reverse=True)

    def save_report(self, trending_repos, filename="ai_agent_trends_report.md"):
        """マークダウンレポートを保存する"""
        report = "# AI Agent トレンドレポート\n\n"
        report += f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        if not trending_repos:
            report += "トレンドのあるリポジトリは見つかりませんでした。\n"
            return
            
        for repo in trending_repos:
            report += f"## [{repo['name']}]({repo['url']})\n\n"
            report += f"**説明**: {repo['description']}\n\n"
            report += f"**統計**:\n"
            report += f"- スター数: {repo['stars']} (1日あたり {repo['stars_per_day']})\n"
            report += f"- フォーク数: {repo['forks']} (1日あたり {repo['forks_per_day']})\n"
            report += f"- 作成日: {repo['created_at']}\n"
            
            # Add owner information
            owner = repo['owner']
            report += f"\n**作成者情報**:\n"
            report += f"- 名前: {owner['name'] or owner['username']}\n"
            if owner['twitter']:
                report += f"- Twitter: [@{owner['twitter']}](https://twitter.com/{owner['twitter']})\n"
            if owner['blog']:
                report += f"- ブログ/サイト: {owner['blog']}\n"

            report += f"\n**トークン情報**:\n"
            if repo['has_token']:
                report += "- トークンの存在が確認されました\n"
                if repo['token_details']:
                    report += "- 関連キーワード: " + ", ".join(repo['token_details']) + "\n"
            else:
                report += "- トークンの存在は確認されませんでした\n"
            report += "\n"
            
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
        # トークンの有効性をチェック
        analyzer = GitHubTrendAnalyzer()
        if not analyzer.check_token():
            print("エラー: GitHubトークンが無効です。トークンを確認してください。")
            exit(1)
        print("GitHubトークンの確認が完了しました。")
        analyzer.run_analysis()
    except Exception as e:
        print(f"エラーが発生しました: {e}")