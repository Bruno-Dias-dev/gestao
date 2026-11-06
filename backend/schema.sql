CREATE DATABASE IF NOT EXISTS monitoria CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE monitoria;
CREATE TABLE IF NOT EXISTS usuarios (
 id BIGINT PRIMARY KEY AUTO_INCREMENT, nome VARCHAR(120) NOT NULL, email VARCHAR(190) NOT NULL UNIQUE,
 senha_hash VARCHAR(255) NOT NULL, perfil ENUM('admin','usuario') NOT NULL DEFAULT 'usuario',
 ativo BOOLEAN NOT NULL DEFAULT TRUE, criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS projetos (
 id BIGINT PRIMARY KEY AUTO_INCREMENT, nome VARCHAR(180) NOT NULL, descricao TEXT,
 responsavel_id BIGINT NULL, data_inicio DATE NULL, prazo_entrega DATE NULL, data_conclusao DATE NULL,
 status ENUM('Planejamento','Não iniciado','Em andamento','Pausado','Concluído','Cancelado') NOT NULL DEFAULT 'Não iniciado',
 prioridade ENUM('Baixa','Média','Alta','Crítica') NOT NULL DEFAULT 'Média', ativo BOOLEAN NOT NULL DEFAULT TRUE,
 criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
 FOREIGN KEY (responsavel_id) REFERENCES usuarios(id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS tarefas (
 id BIGINT PRIMARY KEY AUTO_INCREMENT, titulo VARCHAR(220) NOT NULL, descricao TEXT, projeto_id BIGINT NULL,
 responsavel_id BIGINT NULL, prioridade ENUM('Baixa','Média','Alta','Crítica') NOT NULL DEFAULT 'Média',
 status ENUM('A fazer','Em andamento','Aguardando terceiros','Finalizado','Cancelado') NOT NULL DEFAULT 'A fazer',
 data_abertura DATE NOT NULL, data_inicio DATE NULL, prazo_entrega DATE NULL, data_conclusao DATE NULL,
 excluido BOOLEAN NOT NULL DEFAULT FALSE, criado_por BIGINT NULL,
 criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
 FOREIGN KEY (projeto_id) REFERENCES projetos(id) ON DELETE SET NULL,
 FOREIGN KEY (responsavel_id) REFERENCES usuarios(id) ON DELETE SET NULL,
 FOREIGN KEY (criado_por) REFERENCES usuarios(id) ON DELETE SET NULL,
 INDEX idx_tarefas_prazo_status (prazo_entrega,status), INDEX idx_tarefas_projeto (projeto_id)
);
CREATE TABLE IF NOT EXISTS historico_tarefas (
 id BIGINT PRIMARY KEY AUTO_INCREMENT, tarefa_id BIGINT NOT NULL, usuario_id BIGINT NULL,
 acao VARCHAR(80) NOT NULL, detalhes TEXT, criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY (tarefa_id) REFERENCES tarefas(id), FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS comentarios_tarefas (
 id BIGINT PRIMARY KEY AUTO_INCREMENT, tarefa_id BIGINT NOT NULL, usuario_id BIGINT NULL,
 comentario TEXT NOT NULL, criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY (tarefa_id) REFERENCES tarefas(id), FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL
);
