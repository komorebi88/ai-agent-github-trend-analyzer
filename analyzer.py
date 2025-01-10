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
                readme_content = base64.b64decode(content).decode('utf-8', errors='ignore')
        return {'readme_content': readme_content}

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
            readme = repo.get('readme_content', '').lower()
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

        return trend_summary[:3] if trend_summary else ["現時点で特筆すべきトレンドは見られません"]

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

    def extract_and_translate_description(self, description, readme_content):
        """リポジトリの説明を抽出して翻訳（2-3行に要約）"""
        
        def clean_text(text):
            """文章のクリーニング"""
            # HTML/Markdownタグと特殊記号の除去
            text = re.sub(r'<[^>]+>', '', text)
            text = re.sub(r'\[\^?\]?[^\]]*\](?:\([^)]*\))?', '', text)
            text = re.sub(r'[#*`|]', '', text)
            # 参照や装飾的な部分の除去
            text = re.sub(r'【[^】]*】', '', text)
            text = re.sub(r'\(.*?\)', '', text)
            return text.strip()

        def get_meaningful_description():
            """意味のある説明文を抽出"""
            if not readme_content and not description:
                return ""

            content_to_analyze = readme_content if readme_content else description
            lines = content_to_analyze.split('\n')
            description_lines = []
            in_description = False

            for line in lines:
                cleaned_line = clean_text(line)
                if not cleaned_line:
                    continue

                # 説明セクションの開始を検出
                if any(x in cleaned_line.lower() for x in ['about', 'description', 'introduction', 'overview']):
                    in_description = True
                    continue

                # 他のセクションの開始を検出したら説明セクションを終了
                if in_description and cleaned_line.startswith(('#', '##', '###')):
                    break

                # 説明として適切な行を収集
                if (len(cleaned_line) > 30 and  # 十分な長さがある
                    not any(x in cleaned_line.lower() for x in [
                        'installation', 'prerequisite', 'license', 'download', 
                        'getting started', 'requirements', 'contribution'
                    ])):
                    description_lines.append(cleaned_line)
                    if len(description_lines) >= 3:  # 最大3行まで
                        break

            return ' '.join(description_lines) if description_lines else description

        def translate_to_japanese(text):
            """説明文を日本語に翻訳と要約"""
            # 専門用語の翻訳辞書
            terms = {
                'artificial intelligence': '人工知能',
                'machine learning': '機械学習',
                'ai agent': 'AIエージェント',
                'agent': 'エージェント',
                'framework': 'フレームワーク',
                'autonomous': '自律型',
                'automation': '自動化',
                'research': '研究',
                'development': '開発',
                'implementation': '実装',
                'platform': 'プラットフォーム',
                'workflow': 'ワークフロー',
                'integration': '統合',
                'language model': '言語モデル',
                'computer use': 'コンピュータ利用',
                'computer interaction': 'コンピュータ操作',
                'decision-making': '意思決定',
                'scientific discovery': '科学的発見'
            }

            # 翻訳処理
            translated = text.lower()
            for eng, jpn in terms.items():
                translated = translated.replace(eng, jpn)

            # 文分割と整形
            sentences = re.split(r'[.。!！?？]', translated)
            valid_sentences = []
            
            for sentence in sentences:
                sentence = sentence.strip().capitalize()
                if len(sentence) > 10:
                    if not sentence.endswith(('。', '.')):
                        sentence += '。'
                    valid_sentences.append(sentence)

            # 2-3行に制限
            return valid_sentences[:2]

        # メイン処理
        desc_text = get_meaningful_description()
        if not desc_text:
            return "説明が提供されていません。"

        translated_sentences = translate_to_japanese(desc_text)
        if not translated_sentences:
            return "説明を解析できませんでした。"

        return '\n'.join(translated_sentences)

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