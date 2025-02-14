from neo4j import GraphDatabase
import time
from typing import List, Dict, Any
import os
from dotenv import load_dotenv


class Neo4jQuerier:
    def __init__(self, uri: str, username: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(username, password))

    def close(self):
        self.driver.close()

    def measure_query_time(self, query: str, params: Dict = None) -> tuple[List[Dict[str, Any]], float]:
        """Execute a query and measure its execution time"""
        with self.driver.session() as session:
            start_time = time.time()
            result = list(session.run(query, params or {}))
            execution_time = time.time() - start_time
            return [dict(record) for record in result], execution_time

    def drop_indexes(self):
        """Drop all existing indexes"""
        with self.driver.session() as session:
            try:
                session.run("DROP INDEX book_title_index IF EXISTS")
                session.run("DROP INDEX book_year_index IF EXISTS")
                session.run("DROP INDEX book_format_index IF EXISTS")
                session.run("DROP INDEX book_lang_pages_index IF EXISTS")
                session.run("DROP INDEX book_ebook_index IF EXISTS")
                # print("Dropped existing indexes")
            except Exception as e:
                print(f"Error dropping indexes: {str(e)}")
                
    def create_indexes(self):
        """Create indexes for better query performance"""
        with self.driver.session() as session:
            # full-text search index for book titles
            try:
                session.run("""
                    DROP INDEX book_title_index IF EXISTS
                """)
                # print("Dropped existing full-text index")
            except Exception as e:
                print(f"Error dropping index: {str(e)}")

            # full-text index 
            try:
                session.run("""
                    CREATE FULLTEXT INDEX book_title_index 
                    FOR (b:Book) 
                    ON EACH [b.title]
                """)
                print("created full-text index: book_title_index")
            except Exception as e:
                print(f"Error creating full-text index: {str(e)}")
                
             # index for publication year queries (used in multiple queries)
            session.run("""
                CREATE INDEX book_year_index IF NOT EXISTS
                FOR (b:Book) ON b.publication_year
            """)
            print("created index: book_year_index")
            
            # index for format queries (used in aggregation queries)
            session.run("""
                CREATE INDEX book_format_index IF NOT EXISTS
                FOR (b:Book) ON b.format
            """)
            print("created index: book_format_index")
            
            # composite index for language and page count query
            session.run("""
                CREATE INDEX book_lang_pages_index IF NOT EXISTS
                FOR (b:Book) ON (b.language_code, b.page_count)
            """)
            print("created index: book_lang_pages_index")
            
            # index for ebook queries
            session.run("""
                CREATE INDEX book_ebook_index IF NOT EXISTS
                FOR (b:Book) ON b.is_ebook
            """)
            print("created index: book_ebook_index")


    def demonstrate_queries(self):
        """Run all query types and measure their performance"""
        queries = {
            
            # find books published after 2023 (so only 2024)
            "basic search on attribute value": """
                MATCH (b:Book)
                WHERE b.publication_year > 2023
                RETURN b.title, b.publication_year
            """,
            
            # count total number of paperback books
            "aggregation paperback": """
                MATCH (b:Book)
                WHERE b.format = "Paperback"
                RETURN count(b)
            """,
            
            # count total number of hardcover books
            "aggregation hardcover": """
                MATCH (b:Book)
                WHERE b.format = "Hardcover"
                RETURN count(b)
            """,
            
            # count total number of ebooks
            "aggregation ebook": """
                MATCH (b:Book)
                WHERE b.is_ebook = true
                RETURN count(b) as ebookCount
            """,
            
            # find english books with over 10000 pages, sorted by publication year
            "top n entities satisfying a criteria, sorted by an attribute": """
                MATCH (b:Book)
                WHERE b.language_code = "en " and b.publication_year IS NOT NULL and b.page_count > 10000
                RETURN b.title, b.publication_year, b.language_code
                ORDER BY b.publication_year DESC
                LIMIT 300
            """,
            
            # group books by publication year and count them
            "group books by year of publication": """
                MATCH (b:Book)
                WHERE b.publication_year IS NOT NULL
                RETURN b.publication_year as year, count(*) as number_of_books
                ORDER BY year DESC
            """
        }

        fulltext_query = {
            "full text search": """
                CALL db.index.fulltext.queryNodes('book_title_index', $search_term)
                YIELD node, score
                WHERE node.title IS NOT NULL
                RETURN node.title as title, score
                LIMIT 5
            """
        }
        
        # first, drop any existing indexes
        print("dropping existing indexes...")
        self.drop_indexes()
        
        # test queries before creating indexes
        print("\nbefore creating indexes:")
        for name, query in queries.items():
            try:
                results, execution_time = self.measure_query_time(query)
                print(f"{name}: execution time: {execution_time:.10f} seconds")
            except Exception as e:
                print(f"\n{name}:")
                print(f"Error executing query: {str(e)}")

        # create indexes
        print("\ncreating indexes...")
        self.create_indexes()

        # test queries after creating indexes
        print("\nafter creating indexes:")
        for name, query in queries.items():
            try:
                results, execution_time = self.measure_query_time(query)
                print(f"{name}: execution time: {execution_time:.10f} seconds")
            except Exception as e:
                print(f"\n{name}:")
                print(f"Error executing query: {str(e)}")
                
        # test full-text search query
        for name, query in fulltext_query.items():
            try:
                results, execution_time = self.measure_query_time(query, {"search_term": "python programming"})
                print(f"{name}: execution time: {execution_time:.10f} seconds")
            except Exception as e:
                print(f"\n{name}:")
                print(f"Error executing query: {str(e)}")

def main():
   
    # load environment variables
    load_dotenv()
    
    # graphdb connection details
    uri = os.getenv("NEO4J_URI")
    username = os.getenv("NEO4J_USERNAME")
    password = os.getenv("NEO4J_PASSWORD") 

    querier = Neo4jQuerier(uri, username, password)
    try:
        querier.demonstrate_queries()
    finally:
        querier.close()

if __name__ == "__main__":
    main()