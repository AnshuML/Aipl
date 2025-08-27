"""
Improved query service with proper design patterns
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import streamlit as st

from utils.error_handler import handle_errors, ValidationError, logger
from utils.cache_manager import streamlit_cache_with_ttl, QueryCache


@dataclass
class QueryContext:
    """Context object for query processing"""
    query: str
    department: str
    language: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class QueryResult:
    """Result object for query processing"""
    response: str
    confidence: float = 0.0
    sources: List[str] = None
    processing_time: float = 0.0
    cached: bool = False
    
    def __post_init__(self):
        if self.sources is None:
            self.sources = []


class QueryStrategy(ABC):
    """Abstract strategy for query processing"""
    
    @abstractmethod
    def can_handle(self, context: QueryContext) -> bool:
        """Check if this strategy can handle the query"""
        pass
    
    @abstractmethod
    def process(self, context: QueryContext) -> QueryResult:
        """Process the query and return result"""
        pass
    
    @property
    @abstractmethod
    def priority(self) -> int:
        """Strategy priority (lower number = higher priority)"""
        pass


class ProductQueryStrategy(QueryStrategy):
    """Strategy for handling product-related queries"""
    
    def __init__(self, product_scraper):
        self.product_scraper = product_scraper
        self.product_keywords = ['product', 'price', 'buy', 'cost', 'purchase', 'item']
    
    def can_handle(self, context: QueryContext) -> bool:
        return any(keyword in context.query.lower() for keyword in self.product_keywords)
    
    @handle_errors("Failed to process product query")
    def process(self, context: QueryContext) -> QueryResult:
        try:
            products = self.product_scraper.search_products(context.query)
            if not products:
                return QueryResult(response="No products found for your query.")
            
            response = "Here are the top products I found:\n\n"
            sources = []
            
            for product in products[:3]:
                response += f"**{product['name']}**\n"
                response += f"Price: {product['price']}\n"
                if product.get('image_url'):
                    response += f"![Product Image]({product['image_url']})\n"
                response += "\n"
                sources.append(product.get('url', ''))
            
            return QueryResult(
                response=response,
                confidence=0.8,
                sources=sources
            )
        except Exception as e:
            logger.error(f"Product query failed: {e}")
            return QueryResult(response=f"Error searching products: {e}")
    
    @property
    def priority(self) -> int:
        return 1


class DepartmentQueryStrategy(QueryStrategy):
    """Strategy for handling department-specific queries"""
    
    def __init__(self, document_service, translation_service):
        self.document_service = document_service
        self.translation_service = translation_service
    
    def can_handle(self, context: QueryContext) -> bool:
        # Can handle any non-product query
        return True
    
    @handle_errors("Failed to process department query")
    @streamlit_cache_with_ttl(ttl_hours=1)
    def process(self, context: QueryContext) -> QueryResult:
        try:
            # Load department resources
            embeddings, db = self.document_service.load_department_db(context.department)
            if not db:
                return QueryResult(
                    response=f"❌ No index found for {context.department} department"
                )
            
            # Clean query
            clean_query = self._clean_query(context.query)
            
            # Search documents
            docs = db.similarity_search(clean_query, k=15)
            if not docs:
                return QueryResult(
                    response="⚠️ No relevant information found."
                )
            
            # Process and generate response
            response = self._generate_response(clean_query, docs, context)
            
            # Translate if needed
            if context.language != 'en':
                response = self.translation_service.translate_response(
                    response, context.language
                )
            
            return QueryResult(
                response=response,
                confidence=0.9,
                sources=[doc.metadata.get('source', '') for doc in docs[:3]]
            )
            
        except Exception as e:
            logger.error(f"Department query failed: {e}")
            return QueryResult(response=f"❌ Error: {e}")
    
    def _clean_query(self, query: str) -> str:
        """Clean and normalize query"""
        import re
        return re.sub(r"\([^)]*\)|\[[^\]]*\]", "", query).strip()
    
    def _generate_response(self, query: str, docs: List[Any], context: QueryContext) -> str:
        """Generate response from documents"""
        if not docs:
            return "No relevant information found."
        # Return the content of the top-matching document
        return docs[0].page_content if hasattr(docs[0], 'page_content') else str(docs[0])
    
    @property
    def priority(self) -> int:
        return 2


class QueryProcessor:
    """Main query processor using strategy pattern"""
    
    def __init__(self):
        self.strategies: List[QueryStrategy] = []
        self.middleware: List[QueryMiddleware] = []
    
    def add_strategy(self, strategy: QueryStrategy):
        """Add a query processing strategy"""
        self.strategies.append(strategy)
        # Sort by priority
        self.strategies.sort(key=lambda s: s.priority)
    
    def add_middleware(self, middleware: 'QueryMiddleware'):
        """Add middleware for query processing"""
        self.middleware.append(middleware)
    
    @handle_errors("Query processing failed")
    def process_query(self, context: QueryContext) -> QueryResult:
        """Process query using appropriate strategy"""
        # Apply pre-processing middleware
        for middleware in self.middleware:
            context = middleware.pre_process(context)
        
        # Find appropriate strategy
        for strategy in self.strategies:
            if strategy.can_handle(context):
                result = strategy.process(context)
                
                # Apply post-processing middleware
                for middleware in self.middleware:
                    result = middleware.post_process(result, context)
                
                return result
        
        return QueryResult(response="Unable to process your query. Please try rephrasing.")


class QueryMiddleware(ABC):
    """Abstract middleware for query processing"""
    
    @abstractmethod
    def pre_process(self, context: QueryContext) -> QueryContext:
        """Pre-process query context"""
        pass
    
    @abstractmethod
    def post_process(self, result: QueryResult, context: QueryContext) -> QueryResult:
        """Post-process query result"""
        pass


class ValidationMiddleware(QueryMiddleware):
    """Middleware for input validation"""
    
    def pre_process(self, context: QueryContext) -> QueryContext:
        """Validate query context"""
        if not context.query or not context.query.strip():
            raise ValidationError("Query cannot be empty")
        
        if len(context.query) > 1000:
            raise ValidationError("Query too long (max 1000 characters)")
        
        return context
    
    def post_process(self, result: QueryResult, context: QueryContext) -> QueryResult:
        """Validate result"""
        if not result.response:
            result.response = "No response generated"
        
        return result


class LoggingMiddleware(QueryMiddleware):
    """Middleware for logging queries and responses"""
    
    def pre_process(self, context: QueryContext) -> QueryContext:
        """Log incoming query"""
        logger.info(f"Processing query: {context.query[:100]}... (Department: {context.department})")
        return context
    
    def post_process(self, result: QueryResult, context: QueryContext) -> QueryResult:
        """Log query result"""
        logger.info(f"Query processed. Confidence: {result.confidence}, Sources: {len(result.sources)}")
        return result


class PerformanceMiddleware(QueryMiddleware):
    """Middleware for performance monitoring"""
    
    def pre_process(self, context: QueryContext) -> QueryContext:
        """Start performance timer"""
        import time
        context.metadata['start_time'] = time.time()
        return context
    
    def post_process(self, result: QueryResult, context: QueryContext) -> QueryResult:
        """Calculate processing time"""
        import time
        if 'start_time' in context.metadata:
            result.processing_time = time.time() - context.metadata['start_time']
        return result


class QueryServiceFactory:
    """Factory for creating configured query services"""
    
    @staticmethod
    def create_default_service(document_service, product_scraper, translation_service) -> QueryProcessor:
        """Create a query processor with default configuration"""
        processor = QueryProcessor()
        
        # Add strategies
        processor.add_strategy(ProductQueryStrategy(product_scraper))
        processor.add_strategy(DepartmentQueryStrategy(document_service, translation_service))
        
        # Add middleware
        processor.add_middleware(ValidationMiddleware())
        processor.add_middleware(LoggingMiddleware())
        processor.add_middleware(PerformanceMiddleware())
        
        return processor
    
    @staticmethod
    def create_lightweight_service(document_service) -> QueryProcessor:
        """Create a lightweight query processor"""
        processor = QueryProcessor()
        
        # Add only essential strategy
        from services.translation_service import TranslationService
        translation_service = TranslationService()
        processor.add_strategy(DepartmentQueryStrategy(document_service, translation_service))
        
        # Add minimal middleware
        processor.add_middleware(ValidationMiddleware())
        
        return processor