# Database Schema

SQLite by default (`instance/platform.db`), swappable to PostgreSQL/Supabase
via `DATABASE_URL`. Defined in `app/models/models.py` with SQLAlchemy ORM.

## Entity overview

```
User 1───* Workspace 1───* Conversation 1───* Message
                 │                │
                 │                └── (Message.citations: JSON list of {document, chunk_id, snippet})
                 ├───* Document 1───* Chunk  (Chunk.embedding: JSON-encoded float vector)
                 ├───* MemoryItem
                 └───* Setting

User 1───* PromptTemplate (optionally scoped to a Workspace)

Skill 1───* SkillExecution *───1 Workspace

Log *───0..1 User, *───0..1 Workspace   (append-only observability trail)
```

## Tables

### users
| column | type | notes |
|---|---|---|
| id | INTEGER PK | |
| username | VARCHAR(80) UNIQUE | |
| email | VARCHAR(120) UNIQUE | |
| password_hash | VARCHAR(255) | bcrypt |
| created_at | DATETIME | |
| last_login_at | DATETIME | nullable |

### workspaces
| column | type | notes |
|---|---|---|
| id | INTEGER PK | |
| user_id | INTEGER FK → users.id | |
| name, category | VARCHAR | |
| created_at | DATETIME | |
| assistant_name, assistant_role, system_prompt | TEXT/VARCHAR | Module 3 config |
| model, temperature, max_tokens | VARCHAR/FLOAT/INTEGER | Module 3 config |
| personality, response_style | VARCHAR | Module 3 config |

### conversations
| column | type | notes |
|---|---|---|
| id | INTEGER PK | |
| workspace_id | INTEGER FK → workspaces.id | |
| title, session_id | VARCHAR | `session_id` is a UUID hex, unique |
| created_at, updated_at | DATETIME | |
| is_pinned | BOOLEAN | |
| tags | VARCHAR | reserved for future tagging UI |

### messages
| column | type | notes |
|---|---|---|
| id | INTEGER PK | |
| conversation_id | INTEGER FK → conversations.id | |
| role | VARCHAR(20) | `user` \| `assistant` \| `system` |
| content | TEXT | |
| created_at | DATETIME | |
| is_pinned | BOOLEAN | |
| token_count | INTEGER | |
| citations | TEXT (JSON) | list of `{document, chunk_id, chunk_index, score, snippet}` |

### documents
| column | type | notes |
|---|---|---|
| id | INTEGER PK | |
| workspace_id | INTEGER FK → workspaces.id | |
| filename, filetype, filepath | VARCHAR | filetype ∈ {pdf, docx, txt, md} |
| summary | TEXT | generated on upload |
| uploaded_at | DATETIME | |
| char_count | INTEGER | |

### chunks
*(doubles as the "Embeddings" table required by the spec — the embedding
vector is stored directly on the chunk row rather than a separate table,
since it's always a 1:1 relationship and this avoids an extra join on every
search.)*

| column | type | notes |
|---|---|---|
| id | INTEGER PK | |
| document_id | INTEGER FK → documents.id | |
| chunk_index | INTEGER | order within the document |
| content | TEXT | |
| embedding | TEXT (JSON float list) | nullable — null falls back to TF-IDF search |

### prompt_templates
| column | type | notes |
|---|---|---|
| id | INTEGER PK | |
| user_id | INTEGER FK → users.id | |
| workspace_id | INTEGER FK → workspaces.id | nullable |
| title, category, content | VARCHAR/TEXT | |
| created_at, updated_at | DATETIME | |
| use_count | INTEGER | |

### skills
| column | type | notes |
|---|---|---|
| id | INTEGER PK | |
| key | VARCHAR(50) UNIQUE | e.g. `summarization` |
| name, description, icon | VARCHAR | |
| prompt_template | TEXT | uses `{input}` placeholder |

### skill_executions
| column | type | notes |
|---|---|---|
| id | INTEGER PK | |
| skill_id | INTEGER FK → skills.id | |
| workspace_id | INTEGER FK → workspaces.id | |
| input_text, output_text | TEXT | |
| created_at | DATETIME | |
| duration_ms | INTEGER | |

### memory_items
| column | type | notes |
|---|---|---|
| id | INTEGER PK | |
| workspace_id | INTEGER FK → workspaces.id | |
| category | VARCHAR(30) | preference \| topic \| discussion \| pinned |
| content | TEXT | |
| weight | INTEGER | frequency/importance counter |
| created_at, last_used_at | DATETIME | |
| is_pinned | BOOLEAN | |

### settings
| column | type | notes |
|---|---|---|
| id | INTEGER PK | |
| workspace_id | INTEGER FK → workspaces.id | |
| key, value | VARCHAR | unique per (workspace_id, key) |

### logs
| column | type | notes |
|---|---|---|
| id | INTEGER PK | |
| user_id | INTEGER FK → users.id | nullable |
| workspace_id | INTEGER FK → workspaces.id | nullable |
| event_type | VARCHAR(50) | chat \| upload \| skill \| auth \| workspace \| search \| prompt |
| message | VARCHAR(500) | |
| input_tokens, output_tokens | INTEGER | |
| latency_ms | INTEGER | |
| created_at | DATETIME | indexed, drives the dashboard's activity feed and cost estimate |

## Cascade rules
Deleting a `User` cascades to their `Workspace`s. Deleting a `Workspace`
cascades to its `Conversation`s, `Document`s, `MemoryItem`s, and `Setting`s.
Deleting a `Conversation` cascades to its `Message`s. Deleting a `Document`
cascades to its `Chunk`s. This keeps the Danger Zone "delete workspace"
action a single, safe operation with no orphaned rows.
