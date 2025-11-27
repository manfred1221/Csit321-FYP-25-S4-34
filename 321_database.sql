--
-- PostgreSQL database dump
--

-- Dumped from database version 16.4
-- Dumped by pg_dump version 16.4

-- Started on 2025-11-27 13:34:26

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- TOC entry 2 (class 3079 OID 41175)
-- Name: vector; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;


--
-- TOC entry 5161 (class 0 OID 0)
-- Dependencies: 2
-- Name: EXTENSION vector; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION vector IS 'vector data type and ivfflat and hnsw access methods';


--
-- TOC entry 968 (class 1247 OID 41072)
-- Name: user_role; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.user_role AS ENUM (
    'ADMIN',
    'RESIDENT',
    'VISITOR',
    'SECURITY'
);


ALTER TYPE public.user_role OWNER TO postgres;

--
-- TOC entry 971 (class 1247 OID 41084)
-- Name: user_status; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.user_status AS ENUM (
    'ACTIVE',
    'INACTIVE',
    'BANNED',
    'PENDING'
);


ALTER TYPE public.user_status OWNER TO postgres;

--
-- TOC entry 268 (class 1255 OID 41605)
-- Name: log_access_update(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.log_access_update() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.access_time = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.log_access_update() OWNER TO postgres;

--
-- TOC entry 305 (class 1255 OID 41549)
-- Name: update_timestamp(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.update_timestamp() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_timestamp() OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 227 (class 1259 OID 42712)
-- Name: access_logs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.access_logs (
    log_id integer NOT NULL,
    access_time timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    recognized_person character varying(100),
    person_type character varying(20),
    confidence double precision,
    access_result character varying(20),
    embedding_id integer,
    CONSTRAINT access_logs_access_result_check CHECK (((access_result)::text = ANY ((ARRAY['granted'::character varying, 'denied'::character varying])::text[]))),
    CONSTRAINT access_logs_confidence_check CHECK (((confidence >= (0)::double precision) AND (confidence <= (1)::double precision))),
    CONSTRAINT access_logs_person_type_check CHECK (((person_type)::text = ANY ((ARRAY['resident'::character varying, 'visitor'::character varying, 'unknown'::character varying])::text[])))
);


ALTER TABLE public.access_logs OWNER TO postgres;

--
-- TOC entry 226 (class 1259 OID 42711)
-- Name: access_logs_log_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.access_logs_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.access_logs_log_id_seq OWNER TO postgres;

--
-- TOC entry 5162 (class 0 OID 0)
-- Dependencies: 226
-- Name: access_logs_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.access_logs_log_id_seq OWNED BY public.access_logs.log_id;


--
-- TOC entry 225 (class 1259 OID 42696)
-- Name: face_embeddings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.face_embeddings (
    embedding_id integer NOT NULL,
    user_type character varying(20),
    reference_id integer NOT NULL,
    embedding public.vector(128),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT face_embeddings_user_type_check CHECK (((user_type)::text = ANY ((ARRAY['resident'::character varying, 'visitor'::character varying])::text[])))
);


ALTER TABLE public.face_embeddings OWNER TO postgres;

--
-- TOC entry 224 (class 1259 OID 42695)
-- Name: face_embeddings_embedding_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.face_embeddings_embedding_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.face_embeddings_embedding_id_seq OWNER TO postgres;

--
-- TOC entry 5163 (class 0 OID 0)
-- Dependencies: 224
-- Name: face_embeddings_embedding_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.face_embeddings_embedding_id_seq OWNED BY public.face_embeddings.embedding_id;


--
-- TOC entry 221 (class 1259 OID 42669)
-- Name: residents; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.residents (
    resident_id integer NOT NULL,
    full_name character varying(100) NOT NULL,
    unit_number character varying(20) NOT NULL,
    contact_number character varying(20),
    user_id integer,
    registered_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.residents OWNER TO postgres;

--
-- TOC entry 220 (class 1259 OID 42668)
-- Name: residents_resident_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.residents_resident_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.residents_resident_id_seq OWNER TO postgres;

--
-- TOC entry 5164 (class 0 OID 0)
-- Dependencies: 220
-- Name: residents_resident_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.residents_resident_id_seq OWNED BY public.residents.resident_id;


--
-- TOC entry 217 (class 1259 OID 42641)
-- Name: roles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.roles (
    role_id integer NOT NULL,
    role_name character varying(50) NOT NULL
);


ALTER TABLE public.roles OWNER TO postgres;

--
-- TOC entry 216 (class 1259 OID 42640)
-- Name: roles_role_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.roles_role_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.roles_role_id_seq OWNER TO postgres;

--
-- TOC entry 5165 (class 0 OID 0)
-- Dependencies: 216
-- Name: roles_role_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.roles_role_id_seq OWNED BY public.roles.role_id;


--
-- TOC entry 219 (class 1259 OID 42650)
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    user_id integer NOT NULL,
    username character varying(100) NOT NULL,
    email character varying(100) NOT NULL,
    password_hash text NOT NULL,
    role_id integer NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.users OWNER TO postgres;

--
-- TOC entry 218 (class 1259 OID 42649)
-- Name: users_user_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.users_user_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_user_id_seq OWNER TO postgres;

--
-- TOC entry 5166 (class 0 OID 0)
-- Dependencies: 218
-- Name: users_user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.users_user_id_seq OWNED BY public.users.user_id;


--
-- TOC entry 223 (class 1259 OID 42684)
-- Name: visitors; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.visitors (
    visitor_id integer NOT NULL,
    full_name character varying(100) NOT NULL,
    contact_number character varying(20),
    visiting_unit character varying(20) NOT NULL,
    check_in timestamp without time zone,
    check_out timestamp without time zone,
    approved_by integer
);


ALTER TABLE public.visitors OWNER TO postgres;

--
-- TOC entry 222 (class 1259 OID 42683)
-- Name: visitors_visitor_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.visitors_visitor_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.visitors_visitor_id_seq OWNER TO postgres;

--
-- TOC entry 5167 (class 0 OID 0)
-- Dependencies: 222
-- Name: visitors_visitor_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.visitors_visitor_id_seq OWNED BY public.visitors.visitor_id;


--
-- TOC entry 4970 (class 2604 OID 42715)
-- Name: access_logs log_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.access_logs ALTER COLUMN log_id SET DEFAULT nextval('public.access_logs_log_id_seq'::regclass);


--
-- TOC entry 4968 (class 2604 OID 42699)
-- Name: face_embeddings embedding_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.face_embeddings ALTER COLUMN embedding_id SET DEFAULT nextval('public.face_embeddings_embedding_id_seq'::regclass);


--
-- TOC entry 4965 (class 2604 OID 42672)
-- Name: residents resident_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.residents ALTER COLUMN resident_id SET DEFAULT nextval('public.residents_resident_id_seq'::regclass);


--
-- TOC entry 4962 (class 2604 OID 42644)
-- Name: roles role_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.roles ALTER COLUMN role_id SET DEFAULT nextval('public.roles_role_id_seq'::regclass);


--
-- TOC entry 4963 (class 2604 OID 42653)
-- Name: users user_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users ALTER COLUMN user_id SET DEFAULT nextval('public.users_user_id_seq'::regclass);


--
-- TOC entry 4967 (class 2604 OID 42687)
-- Name: visitors visitor_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.visitors ALTER COLUMN visitor_id SET DEFAULT nextval('public.visitors_visitor_id_seq'::regclass);


--
-- TOC entry 5155 (class 0 OID 42712)
-- Dependencies: 227
-- Data for Name: access_logs; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.access_logs (log_id, access_time, recognized_person, person_type, confidence, access_result, embedding_id) FROM stdin;
1	2025-11-12 11:06:13.172525	John Tan	resident	0.98	granted	1
2	2025-11-12 11:06:13.172525	Unknown	unknown	0.45	denied	\N
\.


--
-- TOC entry 5153 (class 0 OID 42696)
-- Dependencies: 225
-- Data for Name: face_embeddings; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.face_embeddings (embedding_id, user_type, reference_id, embedding, created_at) FROM stdin;
1	resident	1	[0.01,0.02,0.03,0.04,0.05,0.06,0.07,0.08,0.09,0.1,0.11,0.12,0.13,0.14,0.15,0.16,0.17,0.18,0.19,0.2,0.21,0.22,0.23,0.24,0.25,0.26,0.27,0.28,0.29,0.3,0.31,0.32,0.33,0.34,0.35,0.36,0.37,0.38,0.39,0.4,0.41,0.42,0.43,0.44,0.45,0.46,0.47,0.48,0.49,0.5,0.51,0.52,0.53,0.54,0.55,0.56,0.57,0.58,0.59,0.6,0.61,0.62,0.63,0.64,0.65,0.66,0.67,0.68,0.69,0.7,0.71,0.72,0.73,0.74,0.75,0.76,0.77,0.78,0.79,0.8,0.81,0.82,0.83,0.84,0.85,0.86,0.87,0.88,0.89,0.9,0.91,0.92,0.93,0.94,0.95,0.96,0.97,0.98,0.99,1,1.01,1.02,1.03,1.04,1.05,1.06,1.07,1.08,1.09,1.1,1.11,1.12,1.13,1.14,1.15,1.16,1.17,1.18,1.19,1.2,1.21,1.22,1.23,1.24,1.25,1.26,1.27,1.28]	2025-11-12 11:06:13.172525
2	resident	2	[0.02,0.04,0.06,0.08,0.1,0.12,0.14,0.16,0.18,0.2,0.22,0.24,0.26,0.28,0.3,0.32,0.34,0.36,0.38,0.4,0.42,0.44,0.46,0.48,0.5,0.52,0.54,0.56,0.58,0.6,0.62,0.64,0.66,0.68,0.7,0.72,0.74,0.76,0.78,0.8,0.82,0.84,0.86,0.88,0.9,0.92,0.94,0.96,0.98,1,1.02,1.04,1.06,1.08,1.1,1.12,1.14,1.16,1.18,1.2,1.22,1.24,1.26,1.28,1.3,1.32,1.34,1.36,1.38,1.4,1.42,1.44,1.46,1.48,1.5,1.52,1.54,1.56,1.58,1.6,1.62,1.64,1.66,1.68,1.7,1.72,1.74,1.76,1.78,1.8,1.82,1.84,1.86,1.88,1.9,1.92,1.94,1.96,1.98,2,2.02,2.04,2.06,2.08,2.1,2.12,2.14,2.16,2.18,2.2,2.22,2.24,2.26,2.28,2.3,2.32,2.34,2.36,2.38,2.4,2.42,2.44,2.46,2.48,2.5,2.52,2.54,2.56]	2025-11-12 11:06:13.172525
\.


--
-- TOC entry 5149 (class 0 OID 42669)
-- Dependencies: 221
-- Data for Name: residents; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.residents (resident_id, full_name, unit_number, contact_number, user_id, registered_at) FROM stdin;
1	John Tan	B-12-05	91234567	2	2025-11-12 11:06:13.172525
2	Alice Lim	B-12-06	91234568	4	2025-11-12 11:06:13.172525
3	Bob Ong	B-12-07	91234569	5	2025-11-12 11:06:13.172525
\.


--
-- TOC entry 5145 (class 0 OID 42641)
-- Dependencies: 217
-- Data for Name: roles; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.roles (role_id, role_name) FROM stdin;
1	Admin
2	Resident
3	Visitor
4	Security
\.


--
-- TOC entry 5147 (class 0 OID 42650)
-- Dependencies: 219
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.users (user_id, username, email, password_hash, role_id, created_at) FROM stdin;
1	admin_user	admin@condo.com	hashed_pw_123	1	2025-11-12 11:06:13.172525
2	john_resident	john@condo.com	hashed_pw_456	2	2025-11-12 11:06:13.172525
3	visitor_mary	mary@guest.com	hashed_pw_789	3	2025-11-12 11:06:13.172525
4	alice_resident	alice@condo.com	hashed_pw_101	2	2025-11-12 11:06:13.172525
5	bob_resident	bob@condo.com	hashed_pw_102	2	2025-11-12 11:06:13.172525
6	charlie_visitor	charlie@guest.com	hashed_pw_103	3	2025-11-12 11:06:13.172525
7	security_sam	sam@security.com	hashed_pw_104	4	2025-11-12 11:06:13.172525
\.


--
-- TOC entry 5151 (class 0 OID 42684)
-- Dependencies: 223
-- Data for Name: visitors; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.visitors (visitor_id, full_name, contact_number, visiting_unit, check_in, check_out, approved_by) FROM stdin;
1	Mary Lee	98765432	B-12-05	2025-11-12 11:06:13.172525	\N	1
2	Charlie Tan	98765433	B-12-06	2025-11-12 11:06:13.172525	\N	1
3	Diana Lee	98765434	B-12-07	2025-11-12 11:06:13.172525	\N	2
\.


--
-- TOC entry 5168 (class 0 OID 0)
-- Dependencies: 226
-- Name: access_logs_log_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.access_logs_log_id_seq', 2, true);


--
-- TOC entry 5169 (class 0 OID 0)
-- Dependencies: 224
-- Name: face_embeddings_embedding_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.face_embeddings_embedding_id_seq', 2, true);


--
-- TOC entry 5170 (class 0 OID 0)
-- Dependencies: 220
-- Name: residents_resident_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.residents_resident_id_seq', 3, true);


--
-- TOC entry 5171 (class 0 OID 0)
-- Dependencies: 216
-- Name: roles_role_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.roles_role_id_seq', 4, true);


--
-- TOC entry 5172 (class 0 OID 0)
-- Dependencies: 218
-- Name: users_user_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.users_user_id_seq', 7, true);


--
-- TOC entry 5173 (class 0 OID 0)
-- Dependencies: 222
-- Name: visitors_visitor_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.visitors_visitor_id_seq', 3, true);


--
-- TOC entry 4995 (class 2606 OID 42721)
-- Name: access_logs access_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.access_logs
    ADD CONSTRAINT access_logs_pkey PRIMARY KEY (log_id);


--
-- TOC entry 4993 (class 2606 OID 42705)
-- Name: face_embeddings face_embeddings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.face_embeddings
    ADD CONSTRAINT face_embeddings_pkey PRIMARY KEY (embedding_id);


--
-- TOC entry 4987 (class 2606 OID 42675)
-- Name: residents residents_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.residents
    ADD CONSTRAINT residents_pkey PRIMARY KEY (resident_id);


--
-- TOC entry 4989 (class 2606 OID 42677)
-- Name: residents residents_user_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.residents
    ADD CONSTRAINT residents_user_id_key UNIQUE (user_id);


--
-- TOC entry 4977 (class 2606 OID 42646)
-- Name: roles roles_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_pkey PRIMARY KEY (role_id);


--
-- TOC entry 4979 (class 2606 OID 42648)
-- Name: roles roles_role_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_role_name_key UNIQUE (role_name);


--
-- TOC entry 4981 (class 2606 OID 42662)
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- TOC entry 4983 (class 2606 OID 42658)
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (user_id);


--
-- TOC entry 4985 (class 2606 OID 42660)
-- Name: users users_username_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_username_key UNIQUE (username);


--
-- TOC entry 4991 (class 2606 OID 42689)
-- Name: visitors visitors_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.visitors
    ADD CONSTRAINT visitors_pkey PRIMARY KEY (visitor_id);


--
-- TOC entry 5000 (class 2606 OID 42722)
-- Name: access_logs access_logs_embedding_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.access_logs
    ADD CONSTRAINT access_logs_embedding_id_fkey FOREIGN KEY (embedding_id) REFERENCES public.face_embeddings(embedding_id) ON DELETE SET NULL;


--
-- TOC entry 4999 (class 2606 OID 42706)
-- Name: face_embeddings face_embeddings_reference_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.face_embeddings
    ADD CONSTRAINT face_embeddings_reference_id_fkey FOREIGN KEY (reference_id) REFERENCES public.residents(resident_id) ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4997 (class 2606 OID 42678)
-- Name: residents residents_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.residents
    ADD CONSTRAINT residents_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- TOC entry 4996 (class 2606 OID 42663)
-- Name: users users_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(role_id) ON DELETE CASCADE;


--
-- TOC entry 4998 (class 2606 OID 42690)
-- Name: visitors visitors_approved_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.visitors
    ADD CONSTRAINT visitors_approved_by_fkey FOREIGN KEY (approved_by) REFERENCES public.residents(resident_id) ON DELETE SET NULL;


-- Completed on 2025-11-27 13:34:26

--
-- PostgreSQL database dump complete
--

