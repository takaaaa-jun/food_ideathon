import os
import sys
import mysql.connector

# --- データベース接続情報 ---
# 設定ファイルを読み込む
current_dir = os.path.dirname(os.path.abspath(__file__))
# core/ から見て2つ上の階層 apps/web/ にあると想定するか、元の場所？
# 元の場所は apps/web/db_connection.cofg
# core/database.py -> apps/web/core/database.py
# parent -> apps/web/core
# parent.parent -> apps/web
config_path = os.path.join(current_dir, '../DB_CONNECTION.cofg'.lower().replace('db_connection', 'db_connection')) 
# Correctly: ../db_connection.cofg
config_path = os.path.abspath(os.path.join(current_dir, '../db_connection.cofg'))
config_vars = {}
with open(config_path, 'r', encoding='utf-8') as f:
    exec(f.read(), {}, config_vars)

DB_CONFIG = config_vars['DB_CONFIG']

def get_db_connection():
    """データベースへの接続を確立する"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"データベース接続エラー: {err}", file=sys.stderr)
        return None

def get_synonyms(cursor, keyword):
    """
    指定されたキーワードの同義語を取得する
    """
    synonyms = {keyword}
    
    # 1. キーワードが normalized_name かどうか確認し、そうなら synonym を取得
    sql_get_synonyms = "SELECT synonym FROM synonym_dictionary WHERE normalized_name = %s"
    cursor.execute(sql_get_synonyms, (keyword,))
    for row in cursor.fetchall():
        synonyms.add(row['synonym'])

    # 2. キーワードが synonym かどうか確認し、そうなら normalized_name を取得
    #    さらに、その normalized_name に紐づく他の synonym も取得
    sql_get_normalized = "SELECT normalized_name FROM synonym_dictionary WHERE synonym = %s"
    cursor.execute(sql_get_normalized, (keyword,))
    normalized_names = [row['normalized_name'] for row in cursor.fetchall()]
    
    for norm_name in normalized_names:
        synonyms.add(norm_name)
        cursor.execute(sql_get_synonyms, (norm_name,))
        for row in cursor.fetchall():
            synonyms.add(row['synonym'])
            
    return list(synonyms)

def get_normalized_name(cursor, keyword):
    """
    指定されたキーワードに対応する normalized_name を取得する
    """
    # 1. キーワードが既に normalized_name として存在するか確認
    sql_check_norm = "SELECT normalized_name FROM synonym_dictionary WHERE normalized_name = %s LIMIT 1"
    cursor.execute(sql_check_norm, (keyword,))
    if cursor.fetchone():
        return keyword

    # 2. キーワードが synonym の場合、対応する normalized_name を取得
    sql_get_norm = "SELECT normalized_name FROM synonym_dictionary WHERE synonym = %s LIMIT 1"
    cursor.execute(sql_get_norm, (keyword,))
    row = cursor.fetchone()
    if row:
        return row['normalized_name']
        
    return None

def unify_keywords(cursor, keywords):
    """
    キーワードリスト内の同義語を統合する。
    同じ normalized_name を持つキーワードが複数ある場合、
    synonym_dictionary 全体の中から id が最も小さいものを代表として返す。
    """
    if not keywords:
        return []

    # 1. 各入力キーワードの normalized_name を取得
    placeholders = ', '.join(['%s'] * len(keywords))
    sql = f"""
        SELECT synonym, normalized_name 
        FROM synonym_dictionary 
        WHERE synonym IN ({placeholders})
    """
    cursor.execute(sql, keywords)
    rows = cursor.fetchall()
    
    # keyword -> normalized_name
    kw_to_norm = {row['synonym']: row['normalized_name'] for row in rows}
    
    # 2. 必要な normalized_name を収集
    seen_norms = set()
    for kw in keywords:
        if kw in kw_to_norm:
            seen_norms.add(kw_to_norm[kw])
            
    # 3. 各 normalized_name について、IDが最小の synonym を取得
    norm_to_best = {}
    if seen_norms:
        placeholders_norm = ', '.join(['%s'] * len(seen_norms))
        sql_best = f"""
            SELECT normalized_name, synonym, id
            FROM synonym_dictionary 
            WHERE normalized_name IN ({placeholders_norm})
            ORDER BY id ASC
        """
        cursor.execute(sql_best, list(seen_norms))
        best_rows = cursor.fetchall()
        
        for row in best_rows:
            norm = row['normalized_name']
            if norm not in norm_to_best:
                norm_to_best[norm] = row['synonym']
    
    # 4. 結果の構築 (入力順序を維持しつつ置換)
    unified_keywords = []
    processed_norms = set()
    
    for kw in keywords:
        if kw in kw_to_norm:
            norm = kw_to_norm[kw]
            if norm not in processed_norms:
                if norm in norm_to_best:
                    unified_keywords.append(norm_to_best[norm])
                processed_norms.add(norm)
        else:
            # DBにないキーワードはそのまま
            unified_keywords.append(kw)
            
    return unified_keywords
