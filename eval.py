"""Run the labeled top-1 evaluation against the local database."""
import asyncio
import json

from app.services.matching import evaluate


if __name__ == "__main__":
    result = asyncio.run(evaluate())
    print(json.dumps(result, indent=2))
    print(f"TOP1_PRECISION={result['top1_precision']:.4f} ({result['correct']}/{result['cases']})")
