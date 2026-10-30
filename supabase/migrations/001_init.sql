-- Khởi tạo CSDL cho Chatbot HUST.
-- Cách chạy: Supabase Dashboard -> SQL Editor -> dán toàn bộ file -> Run.
-- (Hoặc dùng Supabase CLI: supabase db push)

create extension if not exists vector;

-- ------------------------------------------------------------ văn bản gốc
create table if not exists documents (
  id             bigint generated always as identity primary key,
  title          text not null,
  url            text unique,
  doc_type       text,                 -- quy_che | thong_bao | so_tay | ...
  topic          text,                 -- dkhp | hoc_phi | tot_nghiep | ...
  issued_date    date,                 -- ngày ban hành
  effective_date date,                 -- ngày hiệu lực
  applies_to     text,                 -- khoá áp dụng, vd. "K67 trở đi"
  is_active      boolean not null default true,  -- false khi bị văn bản mới thay thế
  content_hash   text,
  crawled_at     timestamptz default now()
);

-- ------------------------------------------------------------ đoạn văn bản (chunk)
-- vector(1024) là số chiều của bge-m3. Đổi model embedding thì đổi số này.
create table if not exists chunks (
  id           bigint generated always as identity primary key,
  document_id  bigint not null references documents(id) on delete cascade,
  chunk_index  int not null,
  section      text,                   -- vd. "Chương II – Điều 12"
  content      text not null,
  embedding    vector(1024),
  tsv          tsvector generated always as (to_tsvector('simple', coalesce(section, '') || ' ' || content)) stored,
  unique (document_id, chunk_index)
);

create index if not exists chunks_embedding_idx on chunks using hnsw (embedding vector_cosine_ops);
create index if not exists chunks_tsv_idx on chunks using gin (tsv);

-- ------------------------------------------------------------ log + feedback
create table if not exists chat_logs (
  id                 uuid primary key,
  session_id         text,
  question           text not null,
  rewritten_question text,
  answer             text,
  chunk_ids          text[],
  model              text,
  refused            boolean default false,
  latency_ms         int,
  created_at         timestamptz default now()
);

create table if not exists feedback (
  id         bigint generated always as identity primary key,
  answer_id  text not null,
  rating     smallint not null check (rating in (-1, 1)),
  comment    text,
  created_at timestamptz default now()
);

-- ------------------------------------------------------------ tìm kiếm hybrid
-- Lấy top theo vector và top theo full-text, gộp bằng Reciprocal Rank Fusion.
-- Ghi chú (T10): websearch_to_tsquery yêu cầu đủ mọi từ; với câu hỏi dài
-- tiếng Việt nhánh full-text có thể ra rỗng. Cải tiến: tách từ khoá trước,
-- nối bằng OR, hoặc dùng pg_trgm.
create or replace function match_chunks(
  query_embedding vector(1024),
  query_text      text,
  match_count     int default 6,
  rrf_k           int default 50
)
returns table (
  id bigint, document_id bigint, section text, content text,
  title text, url text, effective_date date, score float
)
language sql stable
as $$
  with semantic as (
    select c.id, row_number() over (order by c.embedding <=> query_embedding) as rank
    from chunks c join documents d on d.id = c.document_id
    where d.is_active and c.embedding is not null
    order by c.embedding <=> query_embedding
    limit match_count * 4
  ),
  keyword as (
    select c.id,
           row_number() over (order by ts_rank_cd(c.tsv, websearch_to_tsquery('simple', query_text)) desc) as rank
    from chunks c join documents d on d.id = c.document_id
    where d.is_active and c.tsv @@ websearch_to_tsquery('simple', query_text)
    order by ts_rank_cd(c.tsv, websearch_to_tsquery('simple', query_text)) desc
    limit match_count * 4
  )
  select c.id, c.document_id, c.section, c.content, d.title, d.url, d.effective_date,
         coalesce(1.0 / (rrf_k + s.rank), 0.0) + coalesce(1.0 / (rrf_k + k.rank), 0.0) as score
  from semantic s
  full outer join keyword k on s.id = k.id
  join chunks c on c.id = coalesce(s.id, k.id)
  join documents d on d.id = c.document_id
  order by score desc
  limit match_count;
$$;

-- Backend dùng service key nên không cần policy; vẫn bật RLS để khoá truy cập công khai.
alter table documents enable row level security;
alter table chunks    enable row level security;
alter table chat_logs enable row level security;
alter table feedback  enable row level security;
