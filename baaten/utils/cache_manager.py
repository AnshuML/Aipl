"""
Caching utilities for improved performance
"""
import streamlit as st
import hashlib
import pickle
import os
from typing import Any, Callable, Optional
from datetime import datetime, timedelta
from functools import wraps


class CacheManager:
    """Manages application-level caching"""
    
    def __init__(self, cache_dir: str = ".cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
    
    def _get_cache_key(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """Generate cache key from function name and arguments"""
        key_data = f"{func_name}_{str(args)}_{str(sorted(kwargs.items()))}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _get_cache_path(self, cache_key: str) -> str:
        """Get file path for cache key"""
        return os.path.join(self.cache_dir, f"{cache_key}.pkl")
    
    def get(self, cache_key: str, max_age_hours: int = 24) -> Optional[Any]:
        """Get cached value if it exists and is not expired"""
        cache_path = self._get_cache_path(cache_key)
        
        if not os.path.exists(cache_path):
            return None
        
        # Check if cache is expired
        cache_time = datetime.fromtimestamp(os.path.getmtime(cache_path))
        if datetime.now() - cache_time > timedelta(hours=max_age_hours):
            self.delete(cache_key)
            return None
        
        try:
            with open(cache_path, 'rb') as f:
                return pickle.load(f)
        except Exception:
            self.delete(cache_key)
            return None
    
    def set(self, cache_key: str, value: Any) -> bool:
        """Set cached value"""
        try:
            cache_path = self._get_cache_path(cache_key)
            with open(cache_path, 'wb') as f:
                pickle.dump(value, f)
            return True
        except Exception:
            return False
    
    def delete(self, cache_key: str) -> bool:
        """Delete cached value"""
        try:
            cache_path = self._get_cache_path(cache_key)
            if os.path.exists(cache_path):
                os.remove(cache_path)
            return True
        except Exception:
            return False
    
    def clear_all(self) -> bool:
        """Clear all cached values"""
        try:
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.pkl'):
                    os.remove(os.path.join(self.cache_dir, filename))
            return True
        except Exception:
            return False


# Global cache manager instance
cache_manager = CacheManager()


def disk_cache(max_age_hours: int = 24):
    """Decorator for disk-based caching"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = cache_manager._get_cache_key(func.__name__, args, kwargs)
            
            # Try to get from cache
            cached_result = cache_manager.get(cache_key, max_age_hours)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result)
            return result
        
        return wrapper
    return decorator


def streamlit_cache_with_ttl(ttl_hours: int = 1):
    """Streamlit cache with TTL"""
    def decorator(func: Callable) -> Callable:
        @st.cache_data(ttl=ttl_hours * 3600)  # Convert hours to seconds
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator


class EmbeddingCache:
    """Specialized cache for embeddings"""
    
    @staticmethod
    @st.cache_resource
    def load_embeddings(model_name: str):
        """Cache embeddings model loading"""
        from langchain_community.embeddings import HuggingFaceEmbeddings
        
        return HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": False}
        )
    
    @staticmethod
    @st.cache_data(ttl=3600)  # 1 hour TTL
    def get_document_embeddings(texts: list, model_name: str):
        """Cache document embeddings"""
        embeddings = EmbeddingCache.load_embeddings(model_name)
        return embeddings.embed_documents(texts)


class QueryCache:
    """Cache for query results"""
    
    @staticmethod
    @st.cache_data(ttl=1800)  # 30 minutes TTL
    def get_similar_documents(query: str, department: str, k: int = 15):
        """Cache similarity search results"""
        # This would be implemented with actual vector store
        pass
    
    @staticmethod
    @st.cache_data(ttl=3600)  # 1 hour TTL
    def get_bm25_rankings(query: str, documents: list, top_k: int = 5):
        """Cache BM25 ranking results"""
        from rank_bm25 import BM25Okapi
        
        corpus = [doc.lower().split() for doc in documents]
        bm25 = BM25Okapi(corpus)
        tokenized_query = query.lower().split()
        scores = bm25.get_scores(tokenized_query)
        
        # Return top-k indices
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        return top_indices


def clear_all_caches():
    """Clear all application caches"""
    # Clear Streamlit caches
    st.cache_data.clear()
    st.cache_resource.clear()
    
    # Clear disk cache
    cache_manager.clear_all()
    
    st.success("All caches cleared successfully!")


def get_cache_stats():
    """Get cache statistics"""
    cache_files = [f for f in os.listdir(cache_manager.cache_dir) if f.endswith('.pkl')]
    total_size = sum(
        os.path.getsize(os.path.join(cache_manager.cache_dir, f)) 
        for f in cache_files
    )
    
    return {
        'cache_files': len(cache_files),
        'total_size_mb': total_size / (1024 * 1024),
        'cache_dir': cache_manager.cache_dir
    }