"""
Módulo de histórico de preços usando SQLite.
Armazena snapshots de preços para análise de tendências.
"""
import sqlite3
import os
from typing import List, Dict, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class PriceHistory:
    """Gerencia histórico de preços em SQLite."""
    
    def __init__(self, db_path: str = "price_history.db"):
        """
        Args:
            db_path: Caminho do arquivo SQLite
        """
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self) -> None:
        """Inicializa banco de dados e cria tabela se não existir."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Cria tabela snapshots
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                plataforma TEXT NOT NULL,
                titulo TEXT,
                preco REAL NOT NULL,
                moeda TEXT DEFAULT 'BRL',
                data_coleta TEXT NOT NULL,
                parse_status TEXT DEFAULT 'ok',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Cria índices para performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_url_data 
            ON snapshots(url, data_coleta DESC)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_url 
            ON snapshots(url)
        """)
        
        conn.commit()
        conn.close()
        logger.info(f"Banco de dados inicializado: {self.db_path}")
    
    def save_snapshot(self, url: str, plataforma: str, titulo: Optional[str], 
                     preco: float, moeda: str = "BRL", 
                     data_coleta: Optional[str] = None,
                     parse_status: str = "ok") -> bool:
        """
        Salva snapshot de preço.
        
        Args:
            url: URL do produto
            plataforma: Plataforma (ex: "www.amazon.com.br")
            titulo: Título do produto
            preco: Preço do produto
            moeda: Moeda (padrão: BRL)
            data_coleta: Data de coleta (ISO format). Se None, usa agora
            parse_status: Status do parsing (ok, partial, blocked, error)
        
        Returns:
            True se salvou, False se ignorou (duplicado ou inválido)
        """
        # Validações
        if not url or not url.strip():
            return False
        
        if preco is None or preco <= 0:
            return False
        
        # Usa data atual se não fornecida
        if data_coleta is None:
            data_coleta = datetime.now().isoformat()
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Verifica duplicidade: se já existe snapshot com mesma URL 
            # e data_coleta dentro de 2 minutos
            cursor.execute("""
                SELECT id FROM snapshots 
                WHERE url = ? 
                AND ABS(JULIANDAY(?) - JULIANDAY(data_coleta)) * 24 * 60 < 2
            """, (url, data_coleta))
            
            if cursor.fetchone():
                conn.close()
                logger.debug(f"Snapshot duplicado ignorado para {url} em {data_coleta}")
                return False
            
            # Insere novo snapshot
            cursor.execute("""
                INSERT INTO snapshots 
                (url, plataforma, titulo, preco, moeda, data_coleta, parse_status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (url, plataforma, titulo, preco, moeda, data_coleta, parse_status))
            
            conn.commit()
            conn.close()
            logger.debug(f"Snapshot salvo: {url} - R$ {preco} em {data_coleta}")
            return True
        
        except Exception as e:
            logger.exception(f"Erro ao salvar snapshot para {url}: {e}")
            return False
    
    def get_history(self, url: str, limit: int = 30) -> List[Dict[str, Any]]:
        """
        Recupera histórico de preços para uma URL.
        
        Args:
            url: URL do produto
            limit: Número máximo de registros (padrão: 30)
        
        Returns:
            Lista de snapshots ordenados por data_coleta DESC
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Retorna dict-like rows
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    data_coleta,
                    preco,
                    moeda,
                    plataforma,
                    parse_status,
                    titulo
                FROM snapshots
                WHERE url = ?
                ORDER BY data_coleta DESC
                LIMIT ?
            """, (url, limit))
            
            rows = cursor.fetchall()
            conn.close()
            
            # Converte para lista de dicts
            history = []
            for row in rows:
                history.append({
                    'data_coleta': row['data_coleta'],
                    'preco': row['preco'],
                    'moeda': row['moeda'],
                    'plataforma': row['plataforma'],
                    'parse_status': row['parse_status'],
                    'titulo': row['titulo']
                })
            
            return history
        
        except Exception as e:
            logger.exception(f"Erro ao recuperar histórico para {url}: {e}")
            return []


# Instância global
price_history = PriceHistory()

