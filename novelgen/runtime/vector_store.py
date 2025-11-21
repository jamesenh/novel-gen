"""
向量存储抽象接口层
提供与具体实现解耦的向量存储操作接口
"""
import logging
import uuid
import re
import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Union
from contextlib import contextmanager

from novelgen.models import StoryMemoryChunk


logger = logging.getLogger(__name__)


# LangChain embedding 相关导入
try:
    from langchain_openai import OpenAIEmbeddings
    LANGCHAIN_EMBEDDINGS_AVAILABLE = True
except ImportError:
    LANGCHAIN_EMBEDDINGS_AVAILABLE = False
    logger.warning("langchain-openai未安装，无法使用OpenAI embeddings")


class LangChainEmbeddingAdapter:
    """
    LangChain Embeddings 适配器
    将 LangChain 的 Embeddings 接口适配到 ChromaDB 的 EmbeddingFunction 接口
    """
    
    def __init__(self, langchain_embeddings):
        """
        Args:
            langchain_embeddings: LangChain Embeddings 实例（如 OpenAIEmbeddings）
        """
        self.langchain_embeddings = langchain_embeddings
        model_name = getattr(langchain_embeddings, "model", None)
        # 存储模型名称，供 name() 方法返回
        self._name = model_name or langchain_embeddings.__class__.__name__
    
    def name(self) -> str:
        """返回 embedding 函数名称，供 Chroma 记录/比对使用"""
        return self._name
    
    def __call__(self, input: List[str]) -> List[List[float]]:
        """
        ChromaDB EmbeddingFunction 接口要求的调用方法（用于批量文档嵌入）
        
        Args:
            input: 文本列表
            
        Returns:
            嵌入向量列表
        """
        try:
            # 使用 LangChain 的 embed_documents 方法
            embeddings = self.langchain_embeddings.embed_documents(input)
            return embeddings
        except Exception as e:
            logger.error(f"Embedding生成失败: {e}")
            raise
    
    def embed_query(self, text=None, input=None):
        """
        ChromaDB 查询时需要的方法（用于单个查询文本嵌入）
        
        Args:
            text: 查询文本（可以是 str 或 list）
            input: 查询文本（ChromaDB 可能使用此参数名）
            
        Returns:
            嵌入向量列表（ChromaDB 期望 List[List[float]] 格式）
        """
        try:
            # 添加调试日志
            logger.debug(f"embed_query 被调用: text={text} (type: {type(text)}), input={input} (type: {type(input)})")
            
            # 兼容两种参数名
            query_input = text if text is not None else input
            if query_input is None:
                raise ValueError("必须提供 text 或 input 参数")
            
            # 验证输入类型
            if not isinstance(query_input, (str, list)):
                logger.error(f"query_input 类型错误: {type(query_input)}, 值: {query_input}")
                raise ValueError(f"query_input 必须是 str 或 list，但得到 {type(query_input)}")
            
            # 如果是列表，验证所有元素都是字符串
            if isinstance(query_input, list):
                for i, item in enumerate(query_input):
                    if not isinstance(item, str):
                        logger.error(f"query_input[{i}] 类型错误: {type(item)}, 值: {item}")
                        raise ValueError(f"query_input 列表中的所有元素都必须是字符串，但第{i}个元素是 {type(item)}")
            
            # 处理 list 类型（ChromaDB 查询时会传递 list）
            if isinstance(query_input, list):
                # 使用 embed_documents 处理列表
                # 返回格式：List[List[float]]
                embeddings = self.langchain_embeddings.embed_documents(query_input)
                return embeddings
            else:
                # 字符串类型 - 返回嵌套列表格式以兼容 ChromaDB
                embedding = self.langchain_embeddings.embed_query(query_input)
                return [embedding]  # 包装成列表
                
        except Exception as e:
            logger.error(f"查询embedding生成失败: {e}")
            raise


class VectorStoreInterface(ABC):
    """向量存储操作抽象接口"""
    
    @abstractmethod
    def initialize(self) -> bool:
        """初始化向量存储"""
        pass
    
    @abstractmethod
    def add_chunk(self, chunk: StoryMemoryChunk) -> str:
        """添加文本块到向量存储"""
        pass
    
    @abstractmethod
    def add_chunks(self, chunks: List[StoryMemoryChunk]) -> List[str]:
        """批量添加文本块到向量存储"""
        pass
    
    @abstractmethod
    def search_similar(self, query: str, project_id: str, limit: int = 10) -> List[StoryMemoryChunk]:
        """根据查询文本搜索相似的记忆块"""
        pass
    
    @abstractmethod
    def get_chunks_by_project(self, project_id: str, chapter_index: Optional[int] = None) -> List[StoryMemoryChunk]:
        """根据项目ID获取记忆块"""
        pass
    
    @abstractmethod
    def delete_chunks_by_project(self, project_id: str) -> bool:
        """删除指定项目的所有记忆块"""
        pass
    
    @abstractmethod
    def search_memory_with_filters(self, query: str, project_id: str,
                                   content_type: Optional[str] = None,
                                   entities: Optional[List[str]] = None,
                                   tags: Optional[List[str]] = None,
                                   limit: int = 10) -> List[StoryMemoryChunk]:
        """根据查询文本和过滤条件搜索相似的记忆块"""
        pass
    
    @abstractmethod
    def get_chunks_by_entities(self, project_id: str, entity_ids: List[str],
                              chapter_index: Optional[int] = None) -> List[StoryMemoryChunk]:
        """根据实体ID列表获取相关记忆块"""
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """检查向量存储健康状态"""
        pass
    
    @abstractmethod
    def close(self) -> None:
        """关闭向量存储连接"""
        pass


class TextChunker:
    """文本分块工具"""
    
    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def chunk_text(self, text: str, metadata: Dict[str, Any] = None) -> List[str]:
        """将文本分块"""
        if not text:
            return []
        
        # 清理文本
        text = re.sub(r'\s+', ' ', text.strip())
        
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # 如果不是最后一块，尝试在句号、感叹号或问号处分割
            if end < len(text):
                # 寻找最近的句号、感叹号或问号
                sentence_end = max(
                    text.rfind('。', start, end),
                    text.rfind('！', start, end),
                    text.rfind('？', start, end)
                )
                
                if sentence_end > start:
                    end = sentence_end + 1
                else:
                    # 如果找不到句号，尝试在逗号处分割
                    comma_pos = text.rfind('，', start, end)
                    if comma_pos > start:
                        end = comma_pos + 1
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = max(start + 1, end - self.overlap)
        
        return chunks
    
    def create_chunks_from_scene(self, scene_content: str, project_id: str, 
                                chapter_index: Optional[int] = None, 
                                scene_index: Optional[int] = None,
                                content_type: str = "scene") -> List[StoryMemoryChunk]:
        """从场景内容创建记忆块"""
        text_chunks = self.chunk_text(scene_content)
        memory_chunks = []
        
        for i, chunk_text in enumerate(text_chunks):
            chunk = StoryMemoryChunk(
                chunk_id=str(uuid.uuid4()),
                project_id=project_id,
                chapter_index=chapter_index,
                scene_index=scene_index,
                content=chunk_text,
                content_type=content_type,
                created_at=datetime.now()
            )
            memory_chunks.append(chunk)
        
        return memory_chunks


try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False
    logger.warning("ChromaDB未安装，向量存储功能将被禁用")


class ChromaVectorStore(VectorStoreInterface):
    """Chroma向量存储实现"""
    
    def __init__(self, persist_directory: Union[str, Path], 
                 collection_name: str = "novel_memories",
                 embedding_config: Optional['EmbeddingConfig'] = None):
        if not CHROMA_AVAILABLE:
            raise ImportError("ChromaDB未安装，请运行: pip install chromadb")
        
        self.persist_directory = Path(persist_directory)
        self.collection_name = collection_name
        self.embedding_config = embedding_config
        self.client: Optional[chromadb.Client] = None
        self.collection: Optional[chromadb.Collection] = None
        self.embedding_function = None
    
    def initialize(self) -> bool:
        """初始化Chroma向量存储"""
        try:
            if not CHROMA_AVAILABLE:
                logger.error("ChromaDB未安装")
                return False
            
            # 确保目录存在
            self.persist_directory.mkdir(parents=True, exist_ok=True)
            
            # 创建客户端
            self.client = chromadb.PersistentClient(path=str(self.persist_directory))
            
            # 创建 embedding function
            if self.embedding_config and LANGCHAIN_EMBEDDINGS_AVAILABLE:
                try:
                    # 使用 LangChain 1.0 的 OpenAIEmbeddings
                    kwargs = {
                        "model": self.embedding_config.model_name,
                    }
                    
                    if self.embedding_config.api_key:
                        kwargs["api_key"] = self.embedding_config.api_key
                    if self.embedding_config.base_url:
                        kwargs["base_url"] = self.embedding_config.base_url
                    if self.embedding_config.dimensions:
                        kwargs["dimensions"] = self.embedding_config.dimensions
                    
                    # ModelScope API 需要 encoding_format 参数
                    # 设置为 'float' 以获取浮点数格式的向量
                    kwargs["model_kwargs"] = {"encoding_format": "float"}
                    
                    # 设置 chunk_size=1 避免 LangChain 批处理时的索引错误
                    # 这是因为 ModelScope API 的响应格式与 OpenAI 标准格式略有差异
                    kwargs["chunk_size"] = 1
                    
                    # 禁用 LangChain 的 tokenization 处理，强制传递原始字符串
                    # 阿里云 DashScope API 期望接收字符串而不是 token ID
                    kwargs["check_embedding_ctx_length"] = False
                    
                    langchain_embeddings = OpenAIEmbeddings(**kwargs)
                    self.embedding_function = LangChainEmbeddingAdapter(langchain_embeddings)
                    logger.info(f"使用自定义 embedding 模型: {self.embedding_config.model_name}")
                except Exception as e:
                    logger.warning(f"创建自定义 embedding 失败，将使用默认模型: {e}")
                    self.embedding_function = None
            else:
                logger.info("使用 ChromaDB 默认 embedding 模型")
                self.embedding_function = None
            
            # 获取或创建集合
            try:
                # 优先使用 get_or_create_collection（新版本 Chroma 推荐）
                if hasattr(self.client, "get_or_create_collection"):
                    self.collection = self.client.get_or_create_collection(
                        name=self.collection_name,
                        embedding_function=self.embedding_function,
                        metadata={"description": "NovelGen故事记忆向量存储"}
                    )
                    logger.info(f"已获取或创建集合: {self.collection_name}")
                else:
                    # 兼容旧版本：先尝试获取，不存在再创建
                    try:
                        self.collection = self.client.get_collection(
                            name=self.collection_name,
                            embedding_function=self.embedding_function
                        )
                        logger.info(f"获取已存在的集合: {self.collection_name}")
                    except Exception as inner_e:
                        logger.warning(f"获取集合失败，将尝试创建新集合: {inner_e}")
                        self.collection = self.client.create_collection(
                            name=self.collection_name,
                            embedding_function=self.embedding_function,
                            metadata={"description": "NovelGen故事记忆向量存储"}
                        )
                        logger.info(f"创建新集合: {self.collection_name}")
            
            except Exception as e:
                # 典型场景：集合已存在但 embedding_function 或 metadata 不兼容
                if "already exists" in str(e):
                    logger.warning(f"集合已存在且配置不兼容，尝试在兼容模式下重用已有集合: {e}")
                    # 不再传递 embedding_function，避免因配置不一致导致初始化失败
                    self.collection = self.client.get_collection(name=self.collection_name)
                    logger.info(f"在兼容模式下重用已存在集合: {self.collection_name}")
                else:
                    raise
            
            logger.info(f"Chroma向量存储初始化成功: {self.persist_directory}")
            return True
            
        except Exception as e:
            logger.error(f"Chroma向量存储初始化失败: {e}")
            return False
    
    def _chunk_to_document(self, chunk: StoryMemoryChunk) -> Dict[str, Any]:
        """将记忆块转换为Chroma文档格式"""
        return {
            "id": chunk.chunk_id,
            "document": chunk.content,
            "metadata": {
                "project_id": chunk.project_id,
                "chapter_index": chunk.chapter_index,
                "scene_index": chunk.scene_index,
                "content_type": chunk.content_type,
                "entities_mentioned": json.dumps(chunk.entities_mentioned),  # 转为JSON字符串
                "tags": json.dumps(chunk.tags),  # 转为JSON字符串
                "created_at": chunk.created_at.isoformat()
            }
        }
    
    def _document_to_chunk(self, doc: Dict[str, Any]) -> StoryMemoryChunk:
        """将Chroma文档转换为记忆块"""
        metadata = doc.get("metadata", {})
        
        # 解析JSON字符串回列表
        entities_mentioned = metadata.get("entities_mentioned", "[]")
        if isinstance(entities_mentioned, str):
            entities_mentioned = json.loads(entities_mentioned)
        
        tags = metadata.get("tags", "[]")
        if isinstance(tags, str):
            tags = json.loads(tags)
        
        return StoryMemoryChunk(
            chunk_id=doc.get("id", ""),
            project_id=metadata.get("project_id", ""),
            chapter_index=metadata.get("chapter_index"),
            scene_index=metadata.get("scene_index"),
            content=doc.get("document", ""),
            content_type=metadata.get("content_type", "scene"),
            entities_mentioned=entities_mentioned,
            tags=tags,
            embedding_id=doc.get("id", ""),
            created_at=datetime.fromisoformat(metadata.get("created_at", datetime.now().isoformat()))
        )
    
    def add_chunk(self, chunk: StoryMemoryChunk) -> str:
        """添加单个文本块"""
        try:
            if not self.collection:
                raise RuntimeError("向量存储未初始化")
            
            doc = self._chunk_to_document(chunk)
            self.collection.add(
                ids=[doc["id"]],
                documents=[doc["document"]],
                metadatas=[doc["metadata"]]
            )
            
            logger.debug(f"添加记忆块成功: {chunk.chunk_id}")
            return chunk.chunk_id
            
        except Exception as e:
            logger.error(f"添加记忆块失败: {e}")
            raise
    
    def add_chunks(self, chunks: List[StoryMemoryChunk]) -> List[str]:
        """批量添加文本块"""
        try:
            if not self.collection:
                raise RuntimeError("向量存储未初始化")
            
            if not chunks:
                return []
            
            documents = []
            metadatas = []
            ids = []
            
            for chunk in chunks:
                doc = self._chunk_to_document(chunk)
                documents.append(doc["document"])
                metadatas.append(doc["metadata"])
                ids.append(doc["id"])
            
            self.collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
            
            chunk_ids = [chunk.chunk_id for chunk in chunks]
            logger.debug(f"批量添加{len(chunks)}个记忆块成功")
            return chunk_ids
            
        except Exception as e:
            logger.error(f"批量添加记忆块失败: {e}")
            raise
    
    def search_similar(self, query: str, project_id: str, limit: int = 10) -> List[StoryMemoryChunk]:
        """搜索相似记忆块"""
        try:
            if not self.collection:
                raise RuntimeError("向量存储未初始化")
            
            # 使用where子句过滤项目
            results = self.collection.query(
                query_texts=[query],
                n_results=limit,
                where={"project_id": project_id}
            )
            
            chunks = []
            if results["ids"] and results["ids"][0]:
                for i in range(len(results["ids"][0])):
                    doc = {
                        "id": results["ids"][0][i],
                        "document": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i]
                    }
                    chunk = self._document_to_chunk(doc)
                    chunks.append(chunk)
            
            logger.debug(f"搜索到{len(chunks)}个相似记忆块")
            return chunks
            
        except Exception as e:
            logger.error(f"搜索相似记忆块失败: {e}")
            return []
    
    def get_chunks_by_project(self, project_id: str, chapter_index: Optional[int] = None) -> List[StoryMemoryChunk]:
        """根据项目ID获取记忆块"""
        try:
            if not self.collection:
                raise RuntimeError("向量存储未初始化")
            
            # 构建查询条件（ChromaDB需要使用$and操作符组合多个条件）
            if chapter_index is not None:
                where_clause = {
                    "$and": [
                        {"project_id": {"$eq": project_id}},
                        {"chapter_index": {"$eq": chapter_index}}
                    ]
                }
            else:
                where_clause = {"project_id": {"$eq": project_id}}
            
            results = self.collection.get(
                where=where_clause
            )
            
            chunks = []
            if results["ids"]:
                for i in range(len(results["ids"])):
                    doc = {
                        "id": results["ids"][i],
                        "document": results["documents"][i],
                        "metadata": results["metadatas"][i]
                    }
                    chunk = self._document_to_chunk(doc)
                    chunks.append(chunk)
            
            logger.debug(f"获取到{len(chunks)}个记忆块")
            return chunks
            
        except Exception as e:
            logger.error(f"获取记忆块失败: {e}")
            return []
    
    def delete_chunks_by_project(self, project_id: str) -> bool:
        """删除指定项目的所有记忆块"""
        try:
            if not self.collection:
                raise RuntimeError("向量存储未初始化")
            
            # 先获取要删除的chunk IDs
            chunks = self.get_chunks_by_project(project_id)
            if not chunks:
                return True
            
            chunk_ids = [chunk.chunk_id for chunk in chunks]
            self.collection.delete(ids=chunk_ids)
            
            logger.info(f"删除项目{project_id}的{len(chunk_ids)}个记忆块")
            return True
            
        except Exception as e:
            logger.error(f"删除记忆块失败: {e}")
            return False
    
    def search_memory_with_filters(self, query: str, project_id: str,
                                   content_type: Optional[str] = None,
                                   entities: Optional[List[str]] = None,
                                   tags: Optional[List[str]] = None,
                                   limit: int = 10) -> List[StoryMemoryChunk]:
        """根据查询文本和过滤条件搜索相似的记忆块"""
        try:
            if not self.collection:
                raise RuntimeError("向量存储未初始化")
            
            # 构建过滤条件
            where_conditions = [{"project_id": {"$eq": project_id}}]
            
            if content_type:
                where_conditions.append({"content_type": {"$eq": content_type}})
            
            # 注意: ChromaDB元数据中的entities_mentioned和tags是JSON字符串
            # 我们需要过滤后再在Python层面进行精确匹配
            
            where_clause = {"$and": where_conditions} if len(where_conditions) > 1 else where_conditions[0]
            
            # 搜索
            results = self.collection.query(
                query_texts=[query],
                n_results=limit * 2,  # 获取更多结果，用于后续过滤
                where=where_clause
            )
            
            chunks = []
            if results["ids"] and results["ids"][0]:
                for i in range(len(results["ids"][0])):
                    doc = {
                        "id": results["ids"][0][i],
                        "document": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i]
                    }
                    chunk = self._document_to_chunk(doc)
                    
                    # Python层面的entities和tags过滤
                    if entities:
                        if not any(entity in chunk.entities_mentioned for entity in entities):
                            continue
                    
                    if tags:
                        if not any(tag in chunk.tags for tag in tags):
                            continue
                    
                    chunks.append(chunk)
                    
                    if len(chunks) >= limit:
                        break
            
            logger.debug(f"搜索到{len(chunks)}个符合条件的记忆块")
            return chunks
            
        except Exception as e:
            logger.error(f"搜索记忆块失败: {e}")
            return []
    
    def get_chunks_by_entities(self, project_id: str, entity_ids: List[str],
                              chapter_index: Optional[int] = None) -> List[StoryMemoryChunk]:
        """根据实体ID列表获取相关记忆块"""
        try:
            if not self.collection:
                raise RuntimeError("向量存储未初始化")
            
            # 构建 where 条件
            where_conditions = [{"project_id": {"$eq": project_id}}]
            
            if chapter_index is not None:
                where_conditions.append({"chapter_index": {"$eq": chapter_index}})
            
            where_clause = {"$and": where_conditions} if len(where_conditions) > 1 else where_conditions[0]
            
            # 获取所有符合项目条件的记忆块
            results = self.collection.get(where=where_clause)
            
            chunks = []
            if results["ids"]:
                for i in range(len(results["ids"])):
                    doc = {
                        "id": results["ids"][i],
                        "document": results["documents"][i],
                        "metadata": results["metadatas"][i]
                    }
                    chunk = self._document_to_chunk(doc)
                    
                    # 检查是否包含指定的实体
                    if any(entity_id in chunk.entities_mentioned for entity_id in entity_ids):
                        chunks.append(chunk)
            
            logger.debug(f"根据实体获取到{len(chunks)}个记忆块")
            return chunks
            
        except Exception as e:
            logger.error(f"根据实体获取记忆块失败: {e}")
            return []
    
    def health_check(self) -> bool:
        """检查向量存储健康状态"""
        try:
            if not CHROMA_AVAILABLE or not self.collection:
                return False
            
            # 尝试获取集合信息
            count = self.collection.count()
            return count >= 0
            
        except Exception as e:
            logger.error(f"向量存储健康检查失败: {e}")
            return False
    
    def close(self) -> None:
        """关闭向量存储连接"""
        if self.client:
            try:
                # ChromaDB会自动处理持久化
                self.client = None
                self.collection = None
                logger.debug("向量存储连接已关闭")
            except Exception as e:
                logger.warning(f"关闭向量存储连接失败: {e}")


class VectorStoreManager:
    """向量存储管理器，提供降级和错误处理"""
    
    def __init__(self, persist_directory: Union[str, Path], 
                 enabled: bool = True,
                 embedding_config: Optional['EmbeddingConfig'] = None):
        self.enabled = enabled
        self.vector_store: Optional[VectorStoreInterface] = None
        
        # 如果提供了 embedding_config，使用其中的分块配置
        if embedding_config:
            self.chunker = TextChunker(
                chunk_size=embedding_config.chunk_size,
                overlap=embedding_config.chunk_overlap
            )
        else:
            self.chunker = TextChunker()
        
        if self.enabled:
            try:
                self.vector_store = ChromaVectorStore(
                    persist_directory=persist_directory,
                    embedding_config=embedding_config
                )
                if not self.vector_store.initialize():
                    logger.warning("向量存储初始化失败，降级到非持久化模式")
                    self.enabled = False
                    self.vector_store = None
            except Exception as e:
                logger.warning(f"向量存储创建失败，降级到非持久化模式: {e}")
                self.enabled = False
                self.vector_store = None
    
    def is_enabled(self) -> bool:
        """检查向量存储是否启用"""
        return self.enabled and self.vector_store is not None
    
    def add_scene_content(self, content: str, project_id: str, 
                         chapter_index: Optional[int] = None,
                         scene_index: Optional[int] = None) -> List[StoryMemoryChunk]:
        """添加场景内容并自动分块
        
        返回创建的记忆块列表，以便调用者可以将其保存到数据库
        """
        if not self.is_enabled():
            logger.debug("向量存储未启用，跳过场景内容添加")
            return []
        
        try:
            # 使用分块器创建记忆块
            chunks = self.chunker.create_chunks_from_scene(
                content, project_id, chapter_index, scene_index
            )
            
            if chunks:
                chunk_ids = self.vector_store.add_chunks(chunks)
                logger.info(f"场景内容已分块为{len(chunks)}个记忆块，向量ID: {len(chunk_ids)}")
                # 更新记忆块的 embedding_id
                for chunk, embedding_id in zip(chunks, chunk_ids):
                    chunk.embedding_id = embedding_id
                return chunks
            
            return []
            
        except Exception as e:
            logger.warning(f"添加场景内容失败，但不影响主流程: {e}")
            return []
    
    def search_similar(self, query: str, project_id: str, limit: int = 10) -> List[StoryMemoryChunk]:
        """搜索相似记忆（带降级处理）"""
        if not self.is_enabled():
            logger.debug("向量存储未启用，返回空搜索结果")
            return []
        
        try:
            return self.vector_store.search_similar(query, project_id, limit)
        except Exception as e:
            logger.warning(f"搜索相似记忆失败，返回空结果: {e}")
            return []
    
    def get_chunks_by_project(self, project_id: str, chapter_index: Optional[int] = None) -> List[StoryMemoryChunk]:
        """获取项目记忆块（带降级处理）"""
        if not self.is_enabled():
            logger.debug("向量存储未启用，返回空记忆块列表")
            return []
        
        try:
            return self.vector_store.get_chunks_by_project(project_id, chapter_index)
        except Exception as e:
            logger.warning(f"获取记忆块失败，返回空列表: {e}")
            return []
    
    def delete_chunks_by_project(self, project_id: str) -> bool:
        """删除项目记忆块（带降级处理）"""
        if not self.is_enabled():
            logger.debug("向量存储未启用，跳过删除操作")
            return True
        
        try:
            return self.vector_store.delete_chunks_by_project(project_id)
        except Exception as e:
            logger.warning(f"删除记忆块失败，但不影响主流程: {e}")
            return True
    
    def search_memory_with_filters(self, query: str, project_id: str,
                                   content_type: Optional[str] = None,
                                   entities: Optional[List[str]] = None,
                                   tags: Optional[List[str]] = None,
                                   limit: int = 10) -> List[StoryMemoryChunk]:
        """根据查询文本和过滤条件搜索记忆块（带降级处理）"""
        if not self.is_enabled():
            logger.debug("向量存储未启用，返回空搜索结果")
            return []
        
        try:
            return self.vector_store.search_memory_with_filters(
                query, project_id, content_type, entities, tags, limit
            )
        except Exception as e:
            logger.warning(f"搜索记忆块失败，返回空结果: {e}")
            return []
    
    def get_chunks_by_entities(self, project_id: str, entity_ids: List[str],
                              chapter_index: Optional[int] = None) -> List[StoryMemoryChunk]:
        """根据实体ID获取记忆块（带降级处理）"""
        if not self.is_enabled():
            logger.debug("向量存储未启用，返回空记忆块列表")
            return []
        
        try:
            return self.vector_store.get_chunks_by_entities(project_id, entity_ids, chapter_index)
        except Exception as e:
            logger.warning(f"根据实体获取记忆块失败，返回空列表: {e}")
            return []
    
    def health_check(self) -> bool:
        """健康检查"""
        if not self.is_enabled():
            return True  # 降级模式下总是健康的
        
        try:
            return self.vector_store.health_check()
        except Exception as e:
            logger.warning(f"向量存储健康检查失败: {e}")
            return False
    
    def close(self) -> None:
        """关闭向量存储连接"""
        if self.vector_store:
            try:
                self.vector_store.close()
            except Exception as e:
                logger.warning(f"关闭向量存储连接失败: {e}")
