"""
Google Gemini APIを使用したAIサービス
"""
import os
import json
from typing import List, Dict, Any, Optional
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import logging

logger = logging.getLogger(__name__)


class GeminiService:
    """Google Gemini APIを使用したAIサービスクラス"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初期化
        
        Args:
            api_key: Google API Key (指定しない場合は環境変数から取得)
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("Google API Keyが設定されていません")
        
        # Gemini APIの設定
        genai.configure(api_key=self.api_key)
        
        # モデルの初期化
        self.model = genai.GenerativeModel(
            model_name="gemini-pro",
            generation_config={
                "temperature": 0.7,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 2048,
            },
            safety_settings={
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            }
        )
        
        # Vision モデル（画像分析用）
        self.vision_model = genai.GenerativeModel("gemini-pro-vision")
    
    async def generate_questions(self, diary_content: str) -> List[Dict[str, str]]:
        """
        日記の内容から質問を生成
        
        Args:
            diary_content: 日記の内容
            
        Returns:
            生成された質問のリスト
        """
        prompt = f"""
        以下の日記の内容を読んで、書いた人の自己理解を深めるための質問を5つ生成してください。
        質問は具体的で、感情や考えを深掘りするものにしてください。
        
        日記の内容:
        {diary_content}
        
        JSONフォーマットで返してください:
        [
            {{"question": "質問内容", "type": "emotion/thought/action/reflection"}}
        ]
        """
        
        try:
            response = self.model.generate_content(prompt)
            
            # レスポンスのテキストを取得
            text = response.text.strip()
            
            # JSONとして解析を試みる
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
            
            questions = json.loads(text)
            return questions
            
        except Exception as e:
            logger.error(f"質問生成エラー: {e}")
            # フォールバック質問
            return [
                {"question": "今日一番印象に残った出来事は何でしたか？", "type": "reflection"},
                {"question": "その時どんな気持ちでしたか？", "type": "emotion"},
                {"question": "もし違う選択をしていたら、どうなっていたと思いますか？", "type": "thought"},
            ]
    
    async def analyze_emotion(self, text: str) -> Dict[str, Any]:
        """
        テキストから感情を分析
        
        Args:
            text: 分析するテキスト
            
        Returns:
            感情分析結果
        """
        prompt = f"""
        以下のテキストの感情を分析してください。
        
        テキスト:
        {text}
        
        以下のJSONフォーマットで返してください:
        {{
            "emotions": {{
                "joy": 0.0-1.0の数値,
                "sadness": 0.0-1.0の数値,
                "anger": 0.0-1.0の数値,
                "fear": 0.0-1.0の数値,
                "surprise": 0.0-1.0の数値,
                "disgust": 0.0-1.0の数値,
                "neutral": 0.0-1.0の数値
            }},
            "dominant_emotion": "最も強い感情",
            "confidence": 0.0-1.0の信頼度,
            "summary": "感情の要約"
        }}
        """
        
        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
            
            return json.loads(text)
            
        except Exception as e:
            logger.error(f"感情分析エラー: {e}")
            return {
                "emotions": {
                    "joy": 0.0,
                    "sadness": 0.0,
                    "anger": 0.0,
                    "fear": 0.0,
                    "surprise": 0.0,
                    "disgust": 0.0,
                    "neutral": 1.0
                },
                "dominant_emotion": "neutral",
                "confidence": 0.0,
                "summary": "感情を分析できませんでした"
            }
    
    async def chat_consultation(
        self, 
        message: str, 
        context: List[Dict[str, str]] = None
    ) -> str:
        """
        AI相談機能
        
        Args:
            message: ユーザーのメッセージ
            context: 過去の会話コンテキスト
            
        Returns:
            AIの応答
        """
        # コンテキストの構築
        conversation = []
        
        if context:
            for msg in context:
                role = "user" if msg["role"] == "user" else "model"
                conversation.append({"role": role, "parts": [msg["content"]]})
        
        # システムプロンプト
        system_prompt = """
        あなたは優しく共感的なカウンセラーです。
        ユーザーの日記や悩みに対して、以下の点に注意して応答してください：
        1. 共感的で温かい言葉遣い
        2. 判断や批判をしない
        3. 具体的で実践的なアドバイス
        4. 必要に応じて質問を投げかけて、ユーザーの自己理解を深める
        """
        
        # 会話の開始
        chat = self.model.start_chat(history=conversation)
        
        try:
            # システムプロンプトとユーザーメッセージを組み合わせる
            full_message = f"{system_prompt}\n\nユーザー: {message}"
            response = chat.send_message(full_message)
            return response.text
            
        except Exception as e:
            logger.error(f"チャット相談エラー: {e}")
            return "申し訳ございません。現在応答を生成できません。しばらくしてから再度お試しください。"
    
    async def generate_interactive_prompt(self, initial_input: str = None) -> str:
        """
        対話型日記入力のプロンプト生成
        
        Args:
            initial_input: ユーザーの初期入力（オプション）
            
        Returns:
            生成されたプロンプト
        """
        if not initial_input:
            # 初回のプロンプト
            prompts = [
                "今日はどんな一日でしたか？印象に残った出来事を教えてください。",
                "今日の気分はいかがですか？何か心に残ったことはありましたか？",
                "今日という日を一言で表すとしたら、どんな言葉になりますか？",
                "今日あなたが感謝したいことは何ですか？",
                "今日の中で、一番自分らしいと感じた瞬間はいつでしたか？",
            ]
            import random
            return random.choice(prompts)
        
        # フォローアップの質問を生成
        prompt = f"""
        ユーザーが日記に以下の内容を書きました:
        {initial_input}
        
        この内容を深掘りし、より詳細な記録を残すための
        フォローアップの質問を1つ生成してください。
        質問は具体的で、感情や詳細を引き出すものにしてください。
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"プロンプト生成エラー: {e}")
            return "その時、どんな気持ちでしたか？もう少し詳しく教えてください。"
    
    async def extract_keywords(self, text: str, limit: int = 10) -> List[str]:
        """
        テキストからキーワードを抽出
        
        Args:
            text: 分析するテキスト
            limit: 抽出するキーワードの最大数
            
        Returns:
            キーワードのリスト
        """
        prompt = f"""
        以下のテキストから重要なキーワードを最大{limit}個抽出してください。
        固有名詞、感情を表す言葉、行動を表す言葉を優先してください。
        
        テキスト:
        {text}
        
        JSONフォーマットで返してください:
        ["キーワード1", "キーワード2", ...]
        """
        
        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
            
            keywords = json.loads(text)
            return keywords[:limit]
            
        except Exception as e:
            logger.error(f"キーワード抽出エラー: {e}")
            return []