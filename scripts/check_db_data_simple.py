#!/usr/bin/env python3
"""
Simple Database Query Script

This script queries the MongoDB database to check statement_of_claim data
and identify empty fields using pymongo directly.
"""

import os
import sys
import logging
from datetime import datetime
import json
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SimpleDatabaseChecker:
    """Check database data and identify empty fields using pymongo."""
    
    def __init__(self):
        self.db = None
        self.client = None
    
    def connect_to_database(self):
        """Connect to MongoDB database using pymongo."""
        try:
            # Try to import pymongo
            try:
                from pymongo import MongoClient
            except ImportError:
                logger.error("❌ pymongo not installed. Install with: pip install pymongo")
                return False
            
            # Get MongoDB connection string from environment
            mongo_uri = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
            database_name = os.getenv("MONGODB_DATABASE", "maarefa_agent")
            
            logger.info(f"🔗 Connecting to MongoDB: {mongo_uri}")
            logger.info(f"📊 Database: {database_name}")
            
            self.client = MongoClient(mongo_uri)
            self.db = self.client[database_name]
            
            # Test connection
            self.client.admin.command('ping')
            logger.info("✅ Connected to MongoDB database")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to database: {e}")
            return False
    
    def analyze_empty_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze which fields are empty in the data."""
        empty_fields = {}
        non_empty_fields = {}
        
        def check_field(value, field_path=""):
            if value is None:
                empty_fields[field_path] = "null"
            elif isinstance(value, str) and value.strip() == "":
                empty_fields[field_path] = "empty_string"
            elif isinstance(value, str) and value == "غير مذكور":
                empty_fields[field_path] = "غير مذكور"
            elif isinstance(value, list) and len(value) == 0:
                empty_fields[field_path] = "empty_list"
            elif isinstance(value, dict) and len(value) == 0:
                empty_fields[field_path] = "empty_dict"
            else:
                non_empty_fields[field_path] = value
        
        def traverse_dict(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    if isinstance(value, (dict, list)):
                        traverse_dict(value, current_path)
                    else:
                        check_field(value, current_path)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    current_path = f"{path}[{i}]"
                    if isinstance(item, (dict, list)):
                        traverse_dict(item, current_path)
                    else:
                        check_field(item, current_path)
        
        traverse_dict(data)
        
        return {
            "empty_fields": empty_fields,
            "non_empty_fields": non_empty_fields,
            "total_fields": len(empty_fields) + len(non_empty_fields),
            "empty_count": len(empty_fields),
            "non_empty_count": len(non_empty_fields)
        }
    
    def check_statement_of_claim(self, conversation_id: str):
        """Check statement_of_claim collection for specific conversation_id."""
        try:
            if self.db is None:
                logger.error("❌ Database not connected")
                return
            
            logger.info(f"🔍 Querying statement_of_claim collection for conversation_id: {conversation_id}")
            
            # Query the collection
            collection = self.db.statement_of_claim
            document = collection.find_one({"conversation_id": conversation_id})
            
            if not document:
                logger.warning(f"❌ No document found with conversation_id: {conversation_id}")
                return
            
            logger.info("✅ Document found!")
            
            # Convert ObjectId to string for JSON serialization
            if "_id" in document:
                document["_id"] = str(document["_id"])
            
            # Analyze empty fields
            analysis = self.analyze_empty_fields(document)
            
            # Print results
            logger.info("=" * 60)
            logger.info("📊 DATABASE ANALYSIS RESULTS")
            logger.info("=" * 60)
            
            logger.info(f"📈 Total fields: {analysis['total_fields']}")
            logger.info(f"✅ Non-empty fields: {analysis['non_empty_count']}")
            logger.info(f"❌ Empty fields: {analysis['empty_count']}")
            
            if analysis['empty_fields']:
                logger.info("\n❌ EMPTY FIELDS:")
                for field_path, field_type in analysis['empty_fields'].items():
                    logger.info(f"  • {field_path}: {field_type}")
            
            if analysis['non_empty_fields']:
                logger.info("\n✅ NON-EMPTY FIELDS:")
                for field_path, value in analysis['non_empty_fields'].items():
                    # Truncate long values for display
                    display_value = str(value)
                    if len(display_value) > 50:
                        display_value = display_value[:50] + "..."
                    logger.info(f"  • {field_path}: {display_value}")
            
            # Check specific important fields
            logger.info("\n🔍 IMPORTANT FIELDS ANALYSIS:")
            important_fields = [
                "court_info.request_number",
                "plaintiff_info.name",
                "defendant_info.name",
                "case_details.violation_number",
                "additional_info.decision_number",
                "plaintiff_address.mobile",
                "plaintiff_address.email"
            ]
            
            for field_path in important_fields:
                value = self.get_nested_value(document, field_path)
                if value and value != "غير مذكور":
                    logger.info(f"  ✅ {field_path}: {value}")
                else:
                    logger.info(f"  ❌ {field_path}: {'غير مذكور' if value == 'غير مذكور' else 'empty'}")
            
            # Save detailed results to file
            output_file = f"db_analysis_{conversation_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "conversation_id": conversation_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "analysis": analysis,
                    "full_document": document
                }, f, indent=2, ensure_ascii=False)
            
            logger.info(f"\n📄 Detailed analysis saved to: {output_file}")
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Error checking statement_of_claim: {e}")
            return None
    
    def get_nested_value(self, obj: Dict[str, Any], path: str) -> Any:
        """Get nested value from dictionary using dot notation."""
        try:
            keys = path.split('.')
            value = obj
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return None
            return value
        except:
            return None
    
    def list_all_conversations(self):
        """List all conversation_ids in statement_of_claim collection."""
        try:
            if self.db is None:
                logger.error("❌ Database not connected")
                return
            
            collection = self.db.statement_of_claim
            documents = list(collection.find({}, {"conversation_id": 1, "created_at": 1, "_id": 0}))
            
            logger.info(f"📋 Found {len(documents)} documents in statement_of_claim collection:")
            for doc in documents:
                conversation_id = doc.get("conversation_id", "unknown")
                created_at = doc.get("created_at", "unknown")
                logger.info(f"  • {conversation_id} (created: {created_at})")
            
        except Exception as e:
            logger.error(f"❌ Error listing conversations: {e}")
    
    def close_connection(self):
        """Close database connection."""
        if self.client is not None:
            self.client.close()
            logger.info("🔌 Database connection closed")

def main():
    """Main function."""
    conversation_id = "6894a814b2102378323a95d5"
    
    logger.info("🔍 Simple Database Analysis Tool")
    logger.info("=" * 60)
    
    checker = SimpleDatabaseChecker()
    
    # Connect to database
    if not checker.connect_to_database():
        return
    
    try:
        # List all conversations first
        logger.info("\n📋 Listing all conversations in statement_of_claim collection:")
        checker.list_all_conversations()
        
        # Check specific conversation
        logger.info(f"\n🔍 Analyzing conversation: {conversation_id}")
        checker.check_statement_of_claim(conversation_id)
        
    finally:
        checker.close_connection()

if __name__ == "__main__":
    main() 