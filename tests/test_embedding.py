import sys
sys.path.append(".")

from pathlib import Path
from src.ingestion.parser import DocumentParser
from src.ingestion.chunker import SemanticChunker
from src.utils.api_clients import get_embedding_client
from src.utils.config import get_settings
from src.ingestion.chunker import count_tokens

path = Path("data/documents/dsid_5ae656c5449149fa8029551d47d843c3__adr-027-terraform-module-boundaries-and-interface.txt")
chunks = SemanticChunker().chunk(DocumentParser().parse(path))
texts = [c.content for c in chunks]

print("chunk 数量:", len(chunks))
print("配置 batch_size:", get_settings().ingest.batch_size)
print("最长 chunk tokens:", max(count_tokens(t) for t in texts))

client = get_embedding_client()

# 模拟当前 ingest（batch=16）
try:
    client.embed(texts[:16])
    print("前 16 条: 成功")
except Exception as e:
    print("前 16 条: 失败", e)
    if e.__cause__:
        print("  cause:", e.__cause__)

# 符合 API 上限（≤10）
try:
    client.embed(texts[:10])
    print("前 10 条: 成功")
except Exception as e:
    print("前 10 条: 失败", e)
    if e.__cause__:
        print("  cause:", e.__cause__)