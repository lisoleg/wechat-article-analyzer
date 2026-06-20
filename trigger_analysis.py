"""
触发待分析文章的分析（调用 DeepSeek API）
用法: python trigger_analysis.py
"""
import sqlite3
import sys
import json
from pathlib import Path
from datetime import datetime

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

def get_articles_to_analyze(db_path: str) -> list:
    """获取已抓取内容但未分析的文章"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    # 已抓取完成但没有分析结果的文章
    cur.execute("""
        SELECT a.id, a.title, a.url
        FROM articles a
        LEFT JOIN analysis_results r ON a.id = r.article_id
        WHERE a.crawl_status = 'complete' 
          AND r.id IS NULL
        ORDER BY a.id
    """)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_analysis_result(db_path: str, result: dict) -> None:
    """保存分析结果（适配现有表结构）"""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 检查是否已存在
    cur.execute("SELECT id FROM analysis_results WHERE article_id = ?", (result["article_id"],))
    existing = cur.fetchone()

    # 从 DeepSeek 结果中提取数据映射到实际表字段
    concepts_json = json.dumps(result.get("core_concepts", []))
    keywords_json = json.dumps(result.get("key_quotes", []))  # 用 keywords 存 key_quotes
    pillars_json = json.dumps(result.get("theory_pillars", []))
    summary_text = json.dumps(result.get("concept_frequencies", {}), ensure_ascii=False)
    if len(summary_text) > 2000:
        summary_text = summary_text[:2000] + '...'
    # 追加 cross_concept_relations 到 summary
    relations = result.get("cross_concept_relations", [])
    if relations:
        summary_text += " |||RELATIONS||| " + json.dumps(relations, ensure_ascii=False)

    now = datetime.now().isoformat()

    if existing:
        cur.execute("""
            UPDATE analysis_results 
            SET concepts = ?, keywords = ?, theory_pillars = ?,
                summary = ?, analysis_status = ?, analysis_time = ?
            WHERE article_id = ?
        """, (concepts_json, keywords_json, pillars_json, summary_text,
              'complete', now, result["article_id"]))
    else:
        cur.execute("""
            INSERT INTO analysis_results (
                article_id, concepts, keywords, theory_pillars,
                summary, tomas_agi_related, taiji_os_related,
                analysis_status, analysis_time, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 1, 1, ?, ?, ?, ?)
        """, (
            result["article_id"],
            concepts_json,
            keywords_json,
            pillars_json,
            summary_text,
            'complete',
            now,
            now,
            now,
        ))

    conn.commit()
    conn.close()


def analyze_with_deepseek(article: dict, api_key: str) -> dict:
    """使用 DeepSeek API 分析文章"""
    import requests
    
    prompt = f"""请分析以下微信公众号文章，提取以下结构化信息（输出 JSON）：

文章标题：{article.get('title', '')}
文章URL：{article.get('url', '')}

请提取：
1. theory_pillars: 文章涉及的理论支柱（从「刘原理」「三视界法」「太乙预言机」「全息拓扑动力学」中选择）
2. core_concepts: 核心概念列表（每个概念是一个字符串）
3. key_quotes: 关键引述列表（每条引述是一个字符串）
4. concept_frequencies: 概念出现频率（格式：{{"概念名": 出现次数}}）
5. cross_concept_relations: 跨概念关系列表（格式：[{{"source": "概念A", "target": "概念B", "relation": "关系描述"}}]）

请严格输出 JSON 格式，不要有其他内容。"""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
    }
    
    try:
        resp = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        
        # 解析 JSON
        # 尝试从回复中提取 JSON
        import re
        json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
        if json_match:
            content = json_match.group(1)
        
        result = json.loads(content)
        result["article_id"] = article["id"]
        result["model_name"] = "deepseek-chat"
        result["analyzed_at"] = datetime.now().isoformat()
        result["raw_response"] = content
        return result
    except Exception as e:
        print(f"  ❌ API 调用失败: {e}")
        return {"article_id": article["id"], "error": str(e)}


def main():
    import os
    db_path = str(Path(__file__).parent / "data" / "articles.db")
    
    if not Path(db_path).exists():
        print(f"❌ 数据库不存在: {db_path}")
        sys.exit(1)
    
    # 获取 API key
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        print("⚠️ 未设置 DEEPSEEK_API_KEY 环境变量")
        print("请设置: set DEEPSEEK_API_KEY=your_key")
        sys.exit(1)
    
    articles = get_articles_to_analyze(db_path)
    if not articles:
        print("✅ 没有待分析的文章")
        return
    
    print(f"🔍 发现 {len(articles)} 篇待分析文章:")
    for a in articles:
        print(f"  - [{a['id']}] {a['title'][:50]}")
    
    import os
    for article in articles:
        print(f"\n📊 正在分析文章 {article['id']}: {article['title'][:50]}...")
        result = analyze_with_deepseek(article, api_key)
        if "error" not in result:
            save_analysis_result(db_path, result)
            print(f"  ✅ 文章 {article['id']} 分析完成")
        else:
            print(f"  ❌ 文章 {article['id']} 分析失败: {result['error']}")
    
    print("\n✅ 所有待分析文章处理完成！")


if __name__ == "__main__":
    import os
    main()
