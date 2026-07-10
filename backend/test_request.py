from dotenv import load_dotenv
load_dotenv()
from app.api_gemini import generate_argument_tree
try:
    tree = generate_argument_tree("消費税", "テスト議事録")
    print(tree)
except Exception as e:
    print("FATAL ERROR:")
    import traceback
    traceback.print_exc()
