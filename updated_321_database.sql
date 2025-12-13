--
-- PostgreSQL database dump
--

-- Dumped from database version 16.4
-- Dumped by pg_dump version 16.4

-- Started on 2025-12-10 12:37:55

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
-- TOC entry 5240 (class 0 OID 0)
-- Dependencies: 2
-- Name: EXTENSION vector; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION vector IS 'vector data type and ivfflat and hnsw access methods';


--
-- TOC entry 981 (class 1247 OID 41084)
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
-- TOC entry 271 (class 1255 OID 42857)
-- Name: calculate_attendance_duration(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.calculate_attendance_duration() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF NEW.exit_time IS NOT NULL AND NEW.entry_time IS NOT NULL THEN
        NEW.duration_hours = EXTRACT(EPOCH FROM (NEW.exit_time - NEW.entry_time)) / 3600;
    END IF;
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.calculate_attendance_duration() OWNER TO postgres;

--
-- TOC entry 281 (class 1255 OID 41605)
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
-- TOC entry 318 (class 1255 OID 41549)
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
    CONSTRAINT access_logs_person_type_check CHECK (((person_type)::text = ANY ((ARRAY['resident'::character varying, 'visitor'::character varying, 'unknown'::character varying, 'security_officer'::character varying, 'internal_staff'::character varying])::text[])))
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
-- TOC entry 5241 (class 0 OID 0)
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
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    embedding public.vector(512),
    image_filename character varying(255),
    CONSTRAINT face_embeddings_user_type_check CHECK (((user_type)::text = ANY ((ARRAY['resident'::character varying, 'visitor'::character varying, 'security_officer'::character varying, 'internal_staff'::character varying, 'temp_staff'::character varying, 'ADMIN'::character varying])::text[])))
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
-- TOC entry 5242 (class 0 OID 0)
-- Dependencies: 224
-- Name: face_embeddings_embedding_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.face_embeddings_embedding_id_seq OWNED BY public.face_embeddings.embedding_id;


--
-- TOC entry 231 (class 1259 OID 42771)
-- Name: internal_staff; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.internal_staff (
    staff_id integer NOT NULL,
    full_name character varying(100) NOT NULL,
    department character varying(100),
    contact_number character varying(20),
    staff_type character varying(50),
    user_id integer,
    registered_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.internal_staff OWNER TO postgres;

--
-- TOC entry 230 (class 1259 OID 42770)
-- Name: internal_staff_staff_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.internal_staff_staff_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.internal_staff_staff_id_seq OWNER TO postgres;

--
-- TOC entry 5243 (class 0 OID 0)
-- Dependencies: 230
-- Name: internal_staff_staff_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.internal_staff_staff_id_seq OWNED BY public.internal_staff.staff_id;


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
-- TOC entry 5244 (class 0 OID 0)
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
-- TOC entry 5245 (class 0 OID 0)
-- Dependencies: 216
-- Name: roles_role_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.roles_role_id_seq OWNED BY public.roles.role_id;


--
-- TOC entry 229 (class 1259 OID 42746)
-- Name: security_officers; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.security_officers (
    officer_id integer NOT NULL,
    full_name character varying(100) NOT NULL,
    contact_number character varying(20),
    shift character varying(50),
    active boolean DEFAULT true,
    registered_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.security_officers OWNER TO postgres;

--
-- TOC entry 228 (class 1259 OID 42745)
-- Name: security_officers_officer_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.security_officers_officer_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.security_officers_officer_id_seq OWNER TO postgres;

--
-- TOC entry 5246 (class 0 OID 0)
-- Dependencies: 228
-- Name: security_officers_officer_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.security_officers_officer_id_seq OWNED BY public.security_officers.officer_id;


--
-- TOC entry 235 (class 1259 OID 42806)
-- Name: staff; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.staff (
    staff_id integer NOT NULL,
    user_id integer NOT NULL,
    full_name character varying(100) NOT NULL,
    contact_number character varying(20),
    "position" character varying(50),
    face_encoding public.vector(128),
    is_active boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.staff OWNER TO postgres;

--
-- TOC entry 239 (class 1259 OID 42842)
-- Name: staff_attendance; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.staff_attendance (
    attendance_id integer NOT NULL,
    staff_id integer NOT NULL,
    entry_time timestamp without time zone NOT NULL,
    exit_time timestamp without time zone,
    duration_hours numeric(5,2),
    verification_method character varying(50) DEFAULT 'face_recognition'::character varying,
    entry_confidence numeric(3,2),
    exit_confidence numeric(3,2),
    location character varying(100),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.staff_attendance OWNER TO postgres;

--
-- TOC entry 238 (class 1259 OID 42841)
-- Name: staff_attendance_attendance_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.staff_attendance_attendance_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.staff_attendance_attendance_id_seq OWNER TO postgres;

--
-- TOC entry 5247 (class 0 OID 0)
-- Dependencies: 238
-- Name: staff_attendance_attendance_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.staff_attendance_attendance_id_seq OWNED BY public.staff_attendance.attendance_id;


--
-- TOC entry 237 (class 1259 OID 42826)
-- Name: staff_schedules; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.staff_schedules (
    schedule_id integer NOT NULL,
    staff_id integer NOT NULL,
    shift_date date NOT NULL,
    shift_start time without time zone NOT NULL,
    shift_end time without time zone NOT NULL,
    task_description text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.staff_schedules OWNER TO postgres;

--
-- TOC entry 236 (class 1259 OID 42825)
-- Name: staff_schedules_schedule_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.staff_schedules_schedule_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.staff_schedules_schedule_id_seq OWNER TO postgres;

--
-- TOC entry 5248 (class 0 OID 0)
-- Dependencies: 236
-- Name: staff_schedules_schedule_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.staff_schedules_schedule_id_seq OWNED BY public.staff_schedules.schedule_id;


--
-- TOC entry 234 (class 1259 OID 42805)
-- Name: staff_staff_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.staff_staff_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.staff_staff_id_seq OWNER TO postgres;

--
-- TOC entry 5249 (class 0 OID 0)
-- Dependencies: 234
-- Name: staff_staff_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.staff_staff_id_seq OWNED BY public.staff.staff_id;


--
-- TOC entry 233 (class 1259 OID 42784)
-- Name: temp_staff; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.temp_staff (
    temp_id integer NOT NULL,
    full_name character varying(100) NOT NULL,
    company character varying(100),
    contact_number character varying(20),
    contract_start date NOT NULL,
    contract_end date NOT NULL,
    allowed_rate_min integer,
    allowed_rate_max integer,
    user_id integer,
    registered_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.temp_staff OWNER TO postgres;

--
-- TOC entry 232 (class 1259 OID 42783)
-- Name: temp_staff_temp_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.temp_staff_temp_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.temp_staff_temp_id_seq OWNER TO postgres;

--
-- TOC entry 5250 (class 0 OID 0)
-- Dependencies: 232
-- Name: temp_staff_temp_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.temp_staff_temp_id_seq OWNED BY public.temp_staff.temp_id;


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
-- TOC entry 5251 (class 0 OID 0)
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
-- TOC entry 5252 (class 0 OID 0)
-- Dependencies: 222
-- Name: visitors_visitor_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.visitors_visitor_id_seq OWNED BY public.visitors.visitor_id;


--
-- TOC entry 4998 (class 2604 OID 42715)
-- Name: access_logs log_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.access_logs ALTER COLUMN log_id SET DEFAULT nextval('public.access_logs_log_id_seq'::regclass);


--
-- TOC entry 4996 (class 2604 OID 42699)
-- Name: face_embeddings embedding_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.face_embeddings ALTER COLUMN embedding_id SET DEFAULT nextval('public.face_embeddings_embedding_id_seq'::regclass);


--
-- TOC entry 5003 (class 2604 OID 42774)
-- Name: internal_staff staff_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.internal_staff ALTER COLUMN staff_id SET DEFAULT nextval('public.internal_staff_staff_id_seq'::regclass);


--
-- TOC entry 4993 (class 2604 OID 42672)
-- Name: residents resident_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.residents ALTER COLUMN resident_id SET DEFAULT nextval('public.residents_resident_id_seq'::regclass);


--
-- TOC entry 4990 (class 2604 OID 42644)
-- Name: roles role_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.roles ALTER COLUMN role_id SET DEFAULT nextval('public.roles_role_id_seq'::regclass);


--
-- TOC entry 5000 (class 2604 OID 42749)
-- Name: security_officers officer_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.security_officers ALTER COLUMN officer_id SET DEFAULT nextval('public.security_officers_officer_id_seq'::regclass);


--
-- TOC entry 5007 (class 2604 OID 42809)
-- Name: staff staff_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.staff ALTER COLUMN staff_id SET DEFAULT nextval('public.staff_staff_id_seq'::regclass);


--
-- TOC entry 5013 (class 2604 OID 42845)
-- Name: staff_attendance attendance_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.staff_attendance ALTER COLUMN attendance_id SET DEFAULT nextval('public.staff_attendance_attendance_id_seq'::regclass);


--
-- TOC entry 5011 (class 2604 OID 42829)
-- Name: staff_schedules schedule_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.staff_schedules ALTER COLUMN schedule_id SET DEFAULT nextval('public.staff_schedules_schedule_id_seq'::regclass);


--
-- TOC entry 5005 (class 2604 OID 42787)
-- Name: temp_staff temp_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.temp_staff ALTER COLUMN temp_id SET DEFAULT nextval('public.temp_staff_temp_id_seq'::regclass);


--
-- TOC entry 4991 (class 2604 OID 42653)
-- Name: users user_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users ALTER COLUMN user_id SET DEFAULT nextval('public.users_user_id_seq'::regclass);


--
-- TOC entry 4995 (class 2604 OID 42687)
-- Name: visitors visitor_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.visitors ALTER COLUMN visitor_id SET DEFAULT nextval('public.visitors_visitor_id_seq'::regclass);


--
-- TOC entry 5222 (class 0 OID 42712)
-- Dependencies: 227
-- Data for Name: access_logs; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.access_logs (log_id, access_time, recognized_person, person_type, confidence, access_result, embedding_id) FROM stdin;
1	2025-11-12 11:06:13.172525	John Tan	resident	0.98	granted	1
2	2025-11-12 11:06:13.172525	Unknown	unknown	0.45	denied	\N
3	2025-12-04 11:20:09.260757	Joshua Woon	resident	0.5189	granted	14
5	2025-12-04 05:42:33.524844	manual_override	security_officer	1	granted	\N
6	2025-12-04 05:42:48.024068	manual_override	security_officer	1	granted	\N
7	2025-12-04 05:56:38.542444	manual_override	security_officer	1	granted	\N
8	2025-12-04 05:56:47.596649	manual_override	security_officer	1	granted	\N
9	2025-12-04 05:57:27.364894	manual_override	security_officer	1	granted	\N
10	2025-12-04 06:03:08.056747	manual_override	security_officer	1	granted	\N
11	2025-12-04 06:03:38.701477	manual_override	security_officer	1	granted	\N
12	2025-12-04 06:18:14.294973	manual_override	security_officer	1	granted	\N
13	2025-12-04 06:18:48.331988	manual_override	security_officer	1	granted	\N
14	2025-12-04 06:20:03.484271	manual_override	security_officer	1	granted	\N
15	2025-12-04 06:22:30.16923	manual_override	security_officer	1	granted	\N
16	2025-12-04 06:27:45.726498	manual_override	security_officer	1	granted	\N
17	2025-12-04 06:33:46.399522	manual_override	security_officer	1	granted	\N
18	2025-12-04 06:35:42.220713	manual_override	security_officer	1	granted	\N
19	2025-12-04 06:52:24.417011	manual_override	security_officer	1	granted	\N
20	2025-12-04 07:02:49.821224	New Officer	security_officer	1	granted	19
21	2025-12-04 07:03:57.312945	New Officer	security_officer	1	granted	20
22	2025-12-04 07:04:02.875856	New Officer	security_officer	0.8940074443817139	granted	20
23	2025-12-04 07:16:51.851024	Joshua W	security_officer	1	granted	21
24	2025-12-04 07:22:01.978137		security_officer	0.8268131613731384	granted	22
25	2025-12-04 07:24:11.790734		security_officer	0.9681602716445923	granted	23
26	2025-12-04 07:43:09.428045	New Officer	security_officer	1	granted	24
27	2025-12-04 07:43:12.411084	New Officer	security_officer	0.8149482607841492	granted	24
28	2025-12-05 12:28:24.150062	\N	visitor	0.548	denied	20
29	2025-12-08 01:32:13.166772	manual_override	security_officer	1	granted	\N
30	2025-12-08 01:33:30.055203	manual_override	security_officer	1	granted	\N
31	2025-12-08 01:34:25.106945	manual_override	security_officer	1	granted	\N
32	2025-12-08 01:46:54.675664	New Officer	security_officer	1	granted	28
33	2025-12-08 01:47:02.26746	New Officer	security_officer	0.9458483457565308	granted	28
34	2025-12-08 01:47:06.082117	New Officer	security_officer	0.9485343098640442	granted	28
35	2025-12-08 01:47:08.727062	New Officer	security_officer	1	granted	29
36	2025-12-08 01:47:08.802088	New Officer	security_officer	0.9722411036491394	granted	29
37	2025-12-09 10:59:52.688428	Unknown	unknown	0	granted	\N
38	2025-12-09 10:59:57.02983	Unknown	unknown	0	granted	\N
39	2025-12-09 11:00:38.628711	Unknown	unknown	0	granted	\N
40	2025-12-09 11:00:42.927475	Unknown	unknown	0	granted	\N
41	2025-12-09 11:00:46.437443	Unknown	unknown	0	granted	\N
42	2025-12-09 11:04:26.074787	Unknown	unknown	0	granted	\N
43	2025-12-09 11:04:29.245083	Unknown	unknown	0	granted	\N
44	2025-12-09 11:20:43.700758	Unknown	unknown	0	granted	\N
45	2025-12-10 00:29:32.148431	Unknown	unknown	0	granted	\N
46	2025-12-10 00:31:27.26047	New Officer	security_officer	1	granted	30
47	2025-12-10 00:31:32.274314	New Officer	security_officer	0.9721448421478271	granted	30
48	2025-12-10 02:52:41.807799	New Officer	security_officer	1	granted	31
49	2025-12-10 02:52:42.922279	New Officer	security_officer	0.9727696180343628	granted	31
50	2025-12-10 02:52:44.407162	New Officer	security_officer	0.8810933232307434	granted	31
51	2025-12-10 02:52:45.691297	New Officer	security_officer	1	granted	32
\.


--
-- TOC entry 5220 (class 0 OID 42696)
-- Dependencies: 225
-- Data for Name: face_embeddings; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.face_embeddings (embedding_id, user_type, reference_id, created_at, embedding, image_filename) FROM stdin;
1	resident	1	2025-11-12 11:06:13.172525	\N	\N
2	resident	2	2025-11-12 11:06:13.172525	\N	\N
14	resident	20	2025-12-04 02:54:10.311184	[0.6020773,0.64310044,-1.055425,0.33223268,-1.333749,1.393655,0.9864499,0.42688632,-0.6623884,1.6976045,-0.23834512,0.9986988,0.46064124,1.5333138,-0.027603524,-0.09128567,1.5593055,0.4483171,-0.10174297,-0.41029224,0.5386598,-0.62086564,1.1555475,-0.31018186,1.6206324,-1.6414468,-0.7958759,-0.38009378,-0.49498278,-1.659231,0.8357198,0.9326991,-1.4034292,0.9488468,-0.492695,-0.8011708,-0.5872187,-1.332803,-1.0739075,-1.6011653,0.5148565,-0.8673421,-1.5889406,0.81480235,-0.41908494,0.21786186,0.16721351,-1.6076996,1.0673342,-1.13184,-0.0151536465,-1.9861572,1.0279249,-0.66023207,-1.2007276,-0.7595604,-1.5319086,-0.15423313,0.3422944,0.7453392,-0.44155425,0.70029604,-0.4278148,1.7318968,0.0021362118,-0.109556675,0.59151757,-0.62506914,1.3655527,0.20394133,-1.2950476,-1.0967971,1.1833694,1.5708898,1.1631635,0.6479751,-0.5358607,0.056107737,1.7506233,0.679161,0.6702019,-1.2504165,-1.8416646,0.34096968,0.092211,0.8199986,0.2662643,0.82013285,-0.5602469,-0.3071648,-1.7378244,1.522322,-0.80322677,1.328482,0.39432764,-0.19349828,-0.80052525,-0.94456714,-0.49807423,1.5555476,1.4068317,1.3695422,0.60490906,-1.4269948,0.79807067,0.6695793,-1.3462305,-1.7682109,-1.2653902,-0.6896637,-0.058765415,-1.2951643,0.09177635,-0.6604039,-1.7774738,-0.76731914,-0.47747022,-0.47180918,-1.8952396,1.0212204,0.7873526,0.51184857,-0.92809594,0.819369,-0.887333,-1.0119066,1.5008901,0.68337774,1.2578459,-0.07321158,-0.46638072,-0.31483263,-0.06954187,-0.24712044,1.4066839,1.1716238,1.2626486,-0.86911273,-0.19392805,0.43183124,-0.3934347,0.8692081,1.4233631,-0.7864832,-0.27808857,0.28693882,-1.7976321,0.52017236,1.8447357,-0.22891061,-1.0992421,-0.106529675,0.41347542,0.10373803,1.6495112,-0.46331462,-0.12082392,0.24566127,-1.7753611,-0.65747416,0.30450308,1.680486,1.3958762,0.8868209,0.8783717,-0.8211198,-0.95158726,0.93801475,0.31463307,0.5647495,-0.56001395,0.29153478,0.07858792,1.0011079,-2.249786,-0.6021466,-0.42836213,1.8932675,-0.66037464,1.1005312,-0.07834545,0.23640464,0.8806929,0.34474757,0.14649534,-0.8307303,1.4653214,-1.1173198,-0.84664553,-0.85045403,-0.73900735,0.3720668,1.2019212,-0.1435867,0.47870567,1.1310949,-0.6730157,-1.2032067,2.7059102,0.17835616,1.6761588,0.8560041,0.83937603,0.3319422,0.5348931,-1.0394652,-0.37786475,0.41251647,1.0511389,0.55432606,-1.3635615,1.3453424,-1.4046419,1.0784142,-0.37830198,1.5023025,1.1941863,-0.84489685,-0.40035808,0.25444624,1.9456779,3.1412292,2.114359,1.4571906,1.7199645,0.047749355,-0.6239402,-0.55649036,0.017354693,0.81379575,-0.85684025,-0.4412479,0.020042468,-0.848561,-0.9626293,0.89597553,0.057976,-0.78068984,0.8350709,0.17809951,-0.04108494,-0.1201431,-0.48915112,0.30753848,0.7420864,0.68509275,0.026220964,-0.95841634,1.9062201,0.20957677,-0.5235771,0.47256684,0.730521,0.14721489,-0.833437,-1.1639404,0.5159371,0.5518857,-1.0443442,-0.21231982,0.22948547,1.6557305,-0.63290024,-0.46031585,0.74781305,-1.0514292,-0.42839828,-1.3151029,0.79286754,-0.15434918,0.004217826,-1.9121108,-0.1277975,0.6652984,-0.7093356,1.2055385,-1.8612003,-1.8972737,-0.4013674,0.9387681,1.1739355,0.8835549,-2.2060213,0.527697,0.32834235,1.3372995,-1.6164929,-0.69662404,-0.34418377,1.3575802,-0.014085797,0.6027144,1.6183019,-0.6221036,-0.284257,0.31972244,0.03078318,0.24241886,-1.0334811,0.28153276,1.042994,0.49105054,-0.031679034,0.0033268295,-0.08229223,-0.39420867,-0.2177225,-1.6129413,-0.34788066,-2.316481,-1.7318467,-0.5297496,-0.27534577,-1.2169892,1.0843576,-1.6220602,0.7959553,-0.16897541,0.9638722,-1.1941526,-0.3429343,-1.5251416,-0.4548483,-1.3128403,1.2463588,0.0011699405,-0.12132661,-0.16716792,-0.15490198,0.32992205,0.05098216,1.9691379,-2.4916744,-0.49214768,0.21999605,0.9088734,0.9910201,-0.9012337,-0.2706378,-0.20081213,0.61065865,-0.79216194,1.21054,-0.84391147,-0.17832246,0.32627696,0.2010327,0.18035038,-1.9628588,1.538836,1.0947372,-0.25599128,-0.33341205,0.123144574,1.1896812,0.9468769,-0.14318755,1.0531982,-0.77947307,-0.7748225,0.57224065,-0.8228823,-0.8528323,-0.21114135,0.24409828,0.9407557,0.7636373,0.86687815,-1.3083427,0.019753408,-0.08796632,0.38268194,2.5905092,2.0790212,0.14782937,-0.80489707,-1.5358677,1.737616,-1.1539791,0.045437276,-0.37610245,1.6088213,0.1797971,0.20303185,-0.35292774,-0.37110537,-0.8010569,1.6256292,0.006549561,0.9250197,-0.16157214,-1.1333867,-1.0297053,0.9719222,-1.0753429,-0.053835187,-2.3539956,-1.175227,-0.21633796,-0.111258246,-1.4591345,0.08466564,0.81538796,-0.22501162,-0.13192363,-0.07300446,2.497168,1.4359751,0.9636821,-0.15756474,0.48602545,-0.26901188,0.6668613,0.821401,-1.4390101,0.13766858,0.086223625,-1.1073204,0.11574224,-0.8267842,0.1950573,-0.028554855,-0.90198916,1.0136212,1.8653474,0.67552286,-0.40193486,-0.8309829,1.4172748,-1.1899672,-0.87774825,-1.3014758,1.4503895,-1.7324898,1.0799909,-0.46087655,-0.69253093,-0.47509944,0.0038784817,-1.5995085,-0.7786937,-0.16824706,0.80477095,1.264281,0.018121732,-0.093003705,-0.48036385,0.8006097,0.35401934,-0.57389486,0.9380963,-1.023302,0.7710817,-0.39441967,-1.4232917,-0.9233858,-0.44988355,2.771711,1.8859975,0.7512695,0.31164166,2.1278892,1.652411,-0.13163686,-0.6898354,0.9246263,-1.1050817,-0.7574035,0.9706129,-0.9980087,0.21296489,-1.2288997,0.32428935,0.10186382,0.21613586,-0.9544019,-0.5972505,-0.28251928,1.2335955,0.12450084,0.3577131,-0.21574776,-0.9860451,-0.20632483,0.12312787,-1.930809,-0.4743865,-0.70798105,1.3514452,-0.92176455,-0.8621129,-2.5459454,-0.29206723,0.77005184,-0.8855048,-1.9260669,0.82810336,0.47273782,0.37018454,0.44961086,0.87725747,-0.116960086,0.7686557,0.79310864,-1.4987549,-0.6552212,0.32481134,1.2355909,-0.1725524,-1.4093345,-1.9548273,1.0747852]	resident_20.jpg
16	visitor	5	2025-12-04 03:48:11.403466	[-0.3857566,-0.004660381,-1.3238392,-0.3841415,-0.6196386,-0.97621846,-0.29558378,1.709384,-0.13614668,0.07348853,0.79455835,0.90151626,1.3406646,0.5275214,0.7769617,-0.31590238,-0.82235795,-0.78310853,-1.7766385,-0.58503443,-2.1359713,1.2773976,0.47275218,-1.8253536,-0.7774471,0.0070799105,-1.3626416,-0.99691653,1.7606602,-0.8448295,1.2421397,1.585376,1.071394,0.4261341,-0.6902766,-0.18142106,0.08725901,-0.9591836,-0.9213757,0.81491035,0.018582389,-0.14037424,2.225922,0.71452403,0.6144953,-0.42695594,0.35925978,0.71043783,-1.969556,-1.7910235,-0.950488,0.28685573,0.87320536,-2.0381167,-0.7977104,0.89408624,-1.9510462,-0.15756303,-0.21129434,0.39187557,-0.72428817,1.5548561,-1.4056361,-0.06826333,-0.8077502,0.49632922,-1.541501,0.243505,-0.679481,-0.38033512,1.2782174,-0.7186357,0.7920585,0.04148544,0.25147316,-1.4674748,0.52477026,-0.32040602,-1.0052886,-0.86320037,0.9681757,1.3412546,-1.8940071,0.654689,0.4924802,-0.88070315,-0.784385,1.3279341,-0.9373301,-1.1851734,1.376629,-0.4953017,1.8582528,-2.274979,0.1542814,0.4488717,-0.7592927,0.48613378,0.08972806,-0.12781352,0.60069704,1.9553251,1.6646059,0.47188535,-0.1569196,0.010419083,0.26070803,-1.459605,-0.19747098,-0.5428967,0.8699556,1.1541274,-0.40554833,0.28882045,0.52782845,0.6352479,0.10417658,0.463407,-0.42808926,-0.21420293,-0.43008026,0.47296658,-0.002609387,-0.36584485,-1.6054292,-0.9940016,0.60236645,-0.3873824,2.192814,-0.09110385,0.30351752,-0.6526127,1.5855813,0.7660053,-0.58141595,-0.29188415,0.08259648,-1.99561,1.7074723,0.51469886,-0.9077816,0.25023025,-0.6214053,-0.2695397,0.83323056,-0.6997024,-1.9276148,-0.12710315,1.0141957,0.097702764,1.4832008,-0.118951574,-0.30707306,0.94970405,1.8325135,-0.42413396,-0.6693566,-2.0340881,-0.22293028,-1.9862729,1.0746481,0.72297746,0.91244286,-1.062079,2.3419318,-0.6809383,-0.47987258,1.3675463,-1.2097561,0.26787862,-1.5934982,0.16128692,-1.1842097,0.38277933,-0.804649,-0.9486035,0.82614017,0.48189467,0.53194284,0.3473237,-0.19689888,-0.45902628,0.11092949,-0.80697477,0.56441367,0.6487914,-0.15566039,-0.7994062,0.45801032,1.0169371,0.7804895,-0.24133308,0.7102694,0.21331011,1.3304642,1.0811938,0.89052284,0.0005435827,1.015246,-0.46608332,0.26071507,-1.2959155,1.173558,-2.0732653,-0.74541426,-0.057763837,0.91879284,-0.31629357,0.22130036,1.3266656,-0.56115437,1.2444426,-0.13272978,1.1082333,1.118925,0.8921244,-0.20102707,-1.0987358,-1.1129997,-1.9097961,-0.2986001,0.22060335,0.40268025,-0.21526062,0.36166313,-1.2260156,1.1387619,0.047926858,0.27866572,0.95713615,-0.63547397,-0.4115907,0.22321568,-0.2599644,-2.1269484,-0.2501725,-0.18456836,0.17562324,1.842762,-1.3405046,0.5151074,-0.51899815,0.71375024,-1.4726496,-0.6299366,0.06947576,-0.09778502,0.9492637,-1.3485453,1.2882769,0.15550664,1.1427312,-0.1755423,-0.45332664,-0.50479007,0.28579405,0.8602114,-0.5441474,1.3655874,-0.5941285,-0.6393125,-1.2959157,-0.63627696,-0.8138715,1.031487,-0.5525939,-0.5251025,0.5249623,0.021865997,-1.2698286,0.1120179,-0.20514336,1.0299754,0.747484,0.2509922,-0.78676105,0.7470667,1.6556407,0.14568837,2.4823463,1.0523522,1.0115273,0.3835495,-1.6312854,0.5795891,-0.28241408,0.44266367,0.1894955,0.6791666,-0.020582058,0.6809725,0.98128587,-0.7260941,1.097145,0.074895866,1.0911534,-0.1658807,-1.6229835,0.2693003,2.1718206,-0.3817108,0.68612397,-0.14579298,-2.2389815,0.28698584,-0.27023923,0.64971817,-1.13827,-0.4936121,0.40116385,-1.9612339,0.43405694,-0.065472886,-0.26951116,0.4889347,0.09849371,0.6419666,-0.27190244,1.2008829,-0.26965973,-0.8788165,-1.3639532,-0.6869644,0.46656686,-0.33182386,-0.30200753,-1.0875112,2.3502872,-0.25843027,0.59368736,0.70395243,1.30851,-0.9932427,0.75773543,-0.5203528,-0.5063443,-1.0036469,-0.020585975,0.5341038,0.13921452,0.3195263,-0.8229197,0.26046377,0.2533874,1.0679429,-0.48811388,0.31004784,-1.620568,1.4254197,1.5828875,0.9128015,-1.3082528,0.86986625,0.5233877,1.523104,-0.8632503,-1.547712,-0.6877083,0.8760135,-0.36670786,-0.56089973,-1.9083472,-1.8282853,-0.88178784,0.37480792,1.0337945,0.135967,0.9476794,-0.6667714,-1.0502775,0.95868295,-1.6871669,-0.35536903,0.34824735,0.29657593,1.601222,0.3433627,1.3006678,1.566748,-0.74867225,-2.164165,-1.2952261,-0.59609735,-0.6379545,-0.99384385,-0.121206075,0.25412443,-0.902218,0.5857636,-2.0046988,1.2836007,-0.09527939,0.7574887,-0.10873097,1.8641666,0.5428104,0.71094334,1.7855926,-0.3715227,-0.105788715,0.07725584,0.28391564,0.7227684,1.4119384,-0.8254684,0.5732106,-0.15881738,-0.2335662,-0.109835,-0.68395144,1.5237765,0.30131167,1.134762,-1.9350735,-0.0019224207,1.9460275,0.55299526,0.38448074,-0.44540465,-0.12028933,0.38726926,0.7139731,-0.3115076,-0.11890931,-1.0876021,-0.03313932,0.07135937,0.35982576,0.8831541,0.78432083,-1.0497271,0.9032578,-1.0284762,0.10630754,0.27614608,0.35536593,0.033628486,-0.48216906,-1.0752988,1.7302204,0.4249239,0.269841,0.016963672,-0.14985159,1.0740708,-0.3363371,-0.9954558,-1.2625172,1.1069328,-0.36106548,-0.59020066,0.017463973,0.03488369,-0.31963754,0.5795403,1.0566875,-1.0908942,-0.28359595,0.085015714,-0.1445502,0.6923235,-0.6086435,1.0486048,-1.4344476,-0.14683746,-1.2228016,0.78354967,-0.6851815,-1.5807523,2.204423,-0.21012414,1.8087484,0.13493039,-1.0347441,0.0055972487,0.022456853,-0.8918529,-1.0278437,2.1480286,1.7505299,-0.67734647,-0.5409382,-1.6041512,1.3323182,-0.021290824,-2.1048672,-1.5342652,1.0015088,-0.13405779,-1.1728532,0.053106807,-0.8796451,-0.18703252,-1.7549196,0.2447744,-2.191625,0.7083132,-0.01788207,1.2017257,-1.1509022,-1.8638469,0.2322235,-2.262188,0.040874757,-2.6308174,0.73705524,-0.28140888,-1.0566329,0.45307085,-0.44905412,0.7272467,0.6386533]	visitor_5.jpg
19	security_officer	4	2025-12-04 07:02:49.808655	[0.009525298,-0.0038261411,-0.105497055,0.09170176,0.03193423,-0.015040795,-0.034167323,0.011506773,0.010749581,-0.058252104,0.019083114,-0.0031766917,0.017782135,-0.05014772,-0.008815135,-0.060660917,0.054342516,0.09563654,0.064586654,-0.015482028,0.019920235,-0.04920071,0.06217886,-0.058221024,0.016826352,-0.0046419282,0.09480737,-0.028850522,0.012043526,0.006644907,0.05624739,0.015705705,-0.08000182,0.009829801,0.0028260848,-0.0496227,-0.023807885,-0.05507332,-0.115623385,0.087807365,-0.074088275,-0.008957328,-0.047216337,-7.5222697e-06,0.023572491,-0.026746111,0.046710983,0.06854609,-0.060126796,-0.040765423,0.00850649,0.007551832,0.05847754,0.005011678,-0.037086487,0.005964784,-0.009591017,0.05867128,-0.002835241,-0.0007005141,-0.016990758,0.036425587,-0.02610745,-0.0064043524,0.02232125,0.037558973,-0.0022185503,-0.032064054,-0.051664323,-0.100104354,0.0011162899,0.008020976,-0.044560134,-0.01098876,0.04971377,-0.07527064,0.02073557,-0.051578723,0.0078466935,0.009330291,-0.020012507,0.037752908,0.051018596,0.003194102,-0.045822572,0.051453,-0.0018467647,0.065958455,0.01844079,0.029998219,0.0014818953,0.018760974,0.018846141,-0.06567493,0.048824493,0.057339802,0.0046851984,0.02466188,-0.052887596,0.05971257,-0.004755368,-0.05251096,0.01899137,-0.0010203785,-0.024296295,0.047135852,-0.017760275,-0.020665681,-0.017959777,-0.003500365,0.1091012,0.0068800654,-0.042113412,0.01058876,-0.0022364196,0.018125478,0.009795671,0.039713863,-0.05218281,0.13084953,-0.016373416,0.0072006145,0.026500022,0.062216412,-0.04472153,-0.06775469,-0.019106304,-0.0062306947,-0.0018351073,-0.06492173,0.015794285,-0.01517024,0.08841365,-0.0580427,0.014291447,0.094668575,-0.023384541,-0.059466206,0.02437992,0.028745726,-0.02903656,0.031637687,-0.08298681,0.025156382,0.07316192,-0.0058201915,-0.03282683,0.042861342,0.089610904,0.013355974,-0.0058203135,0.0919931,-6.731566e-05,0.062122036,0.044315793,-0.06805853,0.088494964,-0.019391075,0.03176714,-0.030382682,0.070980474,0.053312,0.003719542,0.037410513,0.03421661,0.05233282,-0.053568833,0.009896447,-0.07394298,0.0050867116,-0.039375108,0.03590209,0.040158506,-0.03435815,-0.059223995,-0.0040393677,-0.06078115,-0.019836927,-0.060647294,0.020977216,0.021606812,0.01974074,-0.03288603,0.0760305,0.022459533,0.096737966,-0.04565958,0.017144365,0.028213782,0.065137245,-0.069921955,-0.024918241,0.063429035,-0.0051368107,-0.015173745,0.018762404,0.008146314,0.017797036,0.017699368,-0.009920793,0.031592388,-0.11107619,-0.042538263,0.01896539,0.039567415,-0.041959524,-0.007033312,-0.012001936,-0.009309886,0.049823195,-0.0107414955,0.013995386,-0.019841637,0.028277656,-0.078806326,0.07232437,-0.030747147,0.04992487,0.010482799,-0.02820465,0.010676542,-0.059566088,0.01468712,-0.0043305205,0.01961869,0.072327524,-0.020862976,-0.01599939,-0.03131962,-0.012178941,0.014803896,0.051774308,0.054788426,-0.040006373,0.0025263808,0.052198824,-0.06426086,-0.0068959934,0.05884169,-0.060585342,-0.05892924,-0.020032069,-0.012400129,-0.044949643,0.039203115,0.05196569,-0.05478929,0.018400565,0.04651039,0.033063553,-0.040844966,0.016032888,0.05849523,-0.026411636,0.027238635,-0.016377054,0.06065129,-0.007595049,0.05937608,-0.021592034,-0.01534497,0.009027874,0.00020629574,0.017690558,-0.005755882,-0.039075408,-0.0046304245,-0.032870643,-0.033183057,-0.018075792,-0.06722894,0.04248281,0.0030899125,-0.06421557,-0.008964043,0.013328018,0.010271683,-0.002755046,-0.0013764795,0.03889457,0.037987765,-0.016790936,-0.020122003,0.017280683,0.0007000021,0.00788451,0.024766669,-0.022642642,-0.047177136,0.009938867,0.05696329,-0.06289747,0.03433025,-0.03348648,-0.057584986,0.028525783,0.013838891,0.04277082,0.0959247,0.015103647,0.017756376,0.033180296,-0.016018713,-0.016835546,0.020599497,-0.028054643,0.024944663,0.022477431,-0.05637844,0.010555927,-0.08629272,0.027281767,0.039028957,-0.050175846,0.023506323,0.08927416,0.014937982,-0.046893857,0.08657583,0.022353519,0.08306951,-0.046277467,0.017479094,0.03560701,0.038871046,-0.059736118,0.08140263,0.043905836,0.053331643,0.09846695,-0.014800993,0.11776986,0.003927124,0.06645317,-0.023799248,0.008048442,-0.025049979,0.012476688,0.024723858,-0.010912402,0.03827139,-0.042464077,-0.013440914,0.044814847,0.004447344,0.05467878,0.027356911,0.07579759,0.04759466,0.0044522337,-0.0036281787,-0.01674953,0.023729984,-0.050423514,0.02553087,-0.000781934,0.047379702,0.01275367,0.0061638383,-0.009965385,0.05539329,-0.016081281,-0.10137334,-0.068620875,0.028290253,-0.012391586,0.022954458,-0.067375176,-0.018265888,-0.050453074,-0.05303802,-0.0007751459,-0.0010334081,0.040475704,-0.0042547463,0.03800097,-0.010676982,0.0686202,-0.064548366,-0.051768094,-0.0758218,-0.010189263,-0.011487956,-0.016190574,-0.063198864,-0.044527415,-0.053550187,-0.05187777,0.022545306,-0.0014352774,-0.078916244,0.04919403,-0.0025570733,-0.009795554,0.037907913,0.019383777,-0.009284625,0.106984265,0.041941892,-0.04373307,-0.021465814,0.0015613631,-0.04312123,0.029538427,0.026970029,0.031165866,-0.04643513,0.020580495,0.0207249,-0.039120715,0.022975774,0.005150921,-0.008836251,-0.0055051814,-0.029635184,0.022513967,0.0679723,0.053632986,-0.053508434,0.015957298,0.04646421,0.041794263,-0.005159675,0.113657124,-0.042544458,0.0037791166,0.0003018426,-0.0026055474,0.041849006,-0.026942478,-0.1106188,-0.0154633,0.047384508,-0.021623854,-0.08080611,-0.035865366,-0.02475332,-0.04496004,-0.03935965,0.00632627,0.021155978,0.026022376,-0.0028228397,0.097196475,0.0568453,0.027294084,-0.020088194,-0.020587984,0.0018806348,-0.011452333,0.02099931,0.074912556,-0.013381808,-0.028949138,0.004863521,0.021361625,-0.05037046,0.07690935,0.13215463,0.035781827,0.037391204,0.06627721,-0.060908947,-0.008894951,0.028900655,0.015395923,-0.04907934,0.020170761,0.08905697,0.08785193,0.036730383,0.04611335,0.010133631,0.028440924,-0.009251397,-0.0102366675,-0.018209185,-0.058636446,0.060061034,0.025554802,-0.025115928,-0.029688034,0.040284477,0.06306514,-0.009028002,0.01020058,-0.03811835,0.071767665,0.051593088,-0.0792011,0.03414883,-0.00024220123,-0.060927533,0.04019531,0.07842841,-0.0062377695,0.038281973,0.013674069,0.06469235,0.012993829,-0.030480666,-0.054727998,-0.021425936,0.0016815854,-0.033722945,0.064685024,0.026988087,-0.0028353282,-0.057922196,-0.052740663,0.059281427,0.006619269]	\N
20	security_officer	5	2025-12-04 07:03:57.309946	[0.03104834,0.004390007,-0.030981854,0.048756856,-0.004441358,0.006837205,0.012587415,-0.037943605,-0.05347379,0.09613199,0.034013446,0.011236832,-0.004860666,0.024195276,-0.0032336495,-0.031721372,0.06113157,0.1113542,-0.024208834,0.060866445,0.043938007,-0.022554066,0.07172252,-0.043276537,0.007973801,-0.025407536,0.00670364,0.0031461124,0.009816657,-0.04772013,-0.0044036345,0.033164304,-0.08882215,0.061964676,0.013645668,-0.08465648,-0.023842106,-0.12889864,-0.062697485,0.010223094,-0.051583614,-0.008315982,-0.04269093,0.023419505,0.018623725,0.07642313,0.03898431,-0.029880743,0.023460284,0.020206159,0.017617816,-0.11563676,0.038570486,0.03568939,0.0099560125,-0.104171544,-0.05735194,0.028428417,-0.013490939,0.048313264,-0.018470801,0.053784616,-0.03628586,0.03498141,0.016832942,-0.029984811,0.012492826,-0.019980822,0.021704199,-0.011036167,-0.01850279,0.035611644,-0.0058075576,0.07095517,0.042147826,-0.011899114,0.027038256,0.0074121314,0.032232806,-0.012471116,0.018793924,-0.024315743,0.020110594,-0.038188115,-0.048403833,0.062472247,-0.0051464387,0.0033491703,-0.008312294,0.021358967,-0.0028007983,0.03168475,-0.012210562,-0.0020933424,0.029352669,0.075262785,0.023481224,0.04770147,-0.027055997,0.07370732,0.008517583,0.02868251,0.028527442,0.0006612866,-0.045557164,-0.021587918,-0.023462307,-0.056045808,-0.10986243,-0.00010953215,0.033899333,-0.0753532,0.04265277,-0.017108768,-0.07018925,-0.032004494,-0.01870755,0.008088139,-0.040381733,0.1028186,0.078978695,0.061350957,-0.0015147967,-0.008040897,-0.011578959,-0.05472177,0.0005253194,0.0007283313,0.019156959,-0.0662734,0.0070684496,-0.03454375,-0.037863348,0.028650772,0.012312467,0.018048847,-0.005675395,-0.051813807,-0.027748246,0.060923394,0.0025925997,0.059139352,-0.015278006,-0.0033868183,0.0030870356,0.04068758,-0.05220618,0.013888604,0.063239306,-0.00078247616,-0.021349225,0.05630817,-0.05572832,0.09648968,0.031956136,-0.09013687,-0.08689811,0.002647738,-0.09692555,-0.05983064,0.004377343,0.06915065,-0.03314515,0.09671167,0.04355384,0.03504052,-0.018260414,-0.030640647,-0.041224334,0.009054685,-0.075682975,0.03173266,-0.003271889,0.0038085207,-0.029243052,-0.00613186,-0.020302845,0.10341816,-0.056094,0.0041331477,0.0104234805,0.016950073,0.036184862,0.05439108,0.014486423,-0.027305635,0.053694706,-0.10619536,0.03313392,0.01912595,0.007547258,0.051726524,0.0993088,0.025316497,-0.04073975,0.022220321,-0.1076128,-0.02007973,0.04358482,-0.016145984,0.07674556,0.014451757,-0.02046644,0.03935765,0.05537754,-0.03975206,-0.01199541,0.009137716,-0.0033485487,0.038734253,0.0030731321,0.002817594,-0.02628522,0.02372333,-0.026409335,0.056951415,0.032530077,-0.0060230643,-0.04715818,0.073502176,0.069692284,0.034100037,0.07125233,-0.0005718673,0.02008961,0.07300704,0.025805732,0.02855829,-0.0027217807,0.05324766,0.03947795,0.029264295,-0.012088294,-0.031015528,-0.008171933,0.039872225,-0.07623346,-0.0024784575,0.06017566,0.061143372,-0.045464974,0.039090645,-0.026509799,0.065370314,0.024040386,0.0066366973,-0.02236925,0.0036994903,0.11434583,0.053942524,-0.044819575,0.03433271,0.05656079,-0.05626224,-0.036345832,-0.028258204,-0.0026376275,0.034768976,-0.024079017,0.008186066,-0.035624668,0.03659066,-0.005910028,-0.019555595,-0.016774938,-0.07453866,-0.04833775,-0.011759298,0.024902828,-0.0794105,0.045344725,-0.024720252,0.06086428,0.038424518,0.019283876,0.026544427,-0.038359113,0.0075582676,-0.006758965,0.057662833,0.023026993,0.026111862,-0.11359687,0.016273554,0.0059809363,-0.029719468,0.010423426,-0.016096711,-0.09494435,0.043742754,-0.031271767,-0.00528139,0.008588999,-0.005464721,-0.00016378838,-0.031320635,-0.03559088,0.02049815,-0.057377487,-0.060598176,0.058776252,-0.0025701295,-0.00268453,0.052012026,0.075343214,0.0017126265,0.012549523,0.006874817,-0.031712446,0.0013856833,-0.066951625,0.050908823,0.0002978828,0.0059570856,0.090194166,0.016270945,-0.039318316,-0.027953813,0.08702242,-0.0041146697,0.039220553,-0.052786548,0.03150801,0.004062397,0.033725183,-0.045882262,-0.007545562,-0.00048030494,-0.04314537,0.012954162,-0.035790645,0.05912826,-0.052143726,0.013021534,0.020743215,0.05508039,0.026412385,-0.008180992,-0.060587358,-0.005461758,0.027936384,0.032956824,0.02636514,-0.027645918,0.060992457,0.095114395,-0.021661628,0.07132803,0.017064335,0.04958776,0.046624977,-0.048348278,0.01254728,0.054578125,0.022695739,0.034835793,0.029823516,0.04228847,-0.0060492675,0.00933558,0.020313708,-0.05936037,-0.03756603,-0.012808748,0.0055521885,-0.021167273,-0.018486407,-0.00662593,-0.059340406,-0.0075622317,-0.025470445,0.032355964,0.010746979,0.0520058,-0.043559335,0.08880273,-0.010918588,0.07529482,-0.06426092,0.008859211,-0.0031796924,0.018181643,0.015122983,-0.023364011,0.0025388352,-0.015656576,-0.075826876,0.014961812,-0.049611814,0.057078235,-0.07322811,0.067347325,-0.011812292,0.05458535,0.020491479,0.0040219515,-0.04924098,0.030529741,0.055298146,-0.019944083,-0.017973337,-0.01303594,0.038373433,0.033780273,0.028260035,-0.056226887,0.022692962,0.016380953,0.02657684,0.0062701455,0.001466357,-0.04142892,0.030476356,0.057521008,-0.027327824,-0.046844475,0.07224759,-0.0018276066,0.00790753,-0.05085318,0.031480297,0.04122295,-0.021050882,0.056160048,0.053372752,0.07531503,0.0554549,-0.0364137,-0.0125001455,-0.054189067,-0.03427371,0.018396273,0.030577816,-0.08787834,0.057273827,0.049330987,-0.02219713,-0.04303678,0.0018690658,-0.06314355,-0.08596278,-0.009081968,-0.025438912,0.089738265,0.0011588846,-0.009602499,0.031035064,0.03199471,0.0030693323,-0.06321729,0.062371608,0.0029838611,0.03231676,-0.0013114209,0.0062402734,0.034564275,-0.020764105,0.0812426,0.10528645,0.00876897,0.011495019,0.08857067,-0.009386055,0.008441915,0.005233782,0.046859536,-0.022410393,-0.05052063,0.09458128,0.022634596,0.07354587,0.010216757,0.030856138,0.029029557,0.009781733,0.017647631,0.02202966,-0.03799368,0.059987556,0.054966304,0.039638728,0.058244634,0.0011452074,0.075440735,-0.03737496,-0.071080334,-0.044616178,0.043306395,0.061527412,-0.045810603,-0.05633457,-0.045800563,-0.03919754,0.012404112,0.07098171,-0.070986085,0.028380401,0.068401255,0.043650344,0.025400322,0.0100605665,-0.055766184,0.051069822,-0.044961985,-0.032857083,0.042745005,-0.060572844,0.080518834,-0.026426394,-0.082279295,-0.022897298,0.012323813]	\N
21	security_officer	9	2025-12-04 07:16:51.843146	[0.046130918,0.017033877,-0.03637844,0.08294454,-0.0015167473,-0.0025276842,-0.051949196,-0.010901244,-0.033608258,0.063353635,0.025488464,0.040569596,0.01581118,0.02735568,-0.019918133,-0.06469823,0.06149842,0.09044133,-0.005896022,0.042271413,0.04254371,-0.026289228,0.030386737,-0.042735025,0.014971333,-0.009591176,0.04907413,0.031424202,0.055199936,-0.039869916,0.045426294,0.014063158,-0.045067653,0.029965676,-0.008999009,-0.11107686,-0.087817,-0.102764025,-0.07260946,0.054364838,-0.08978528,-0.0061163157,-0.020623663,0.02240709,0.022079816,0.05651527,0.020308295,-0.014339143,-0.0048260246,-0.00046237098,0.044204168,-0.048780233,0.07706723,0.017451668,-0.014487735,-0.05447039,-0.060325235,0.060693137,-0.030659765,0.02054607,0.01763621,0.04490432,-0.053608328,0.006122789,0.0012180095,0.03186442,-0.010222647,-0.022942714,-0.0040709656,-0.016781488,0.015707364,0.048768368,-0.05745109,0.0775094,0.048696022,-0.017392317,0.011865517,-0.0048796088,0.02002827,0.030662613,0.010955139,0.0060691107,0.021364124,-0.03393982,-0.027118396,0.03071118,0.020887187,0.055043645,-0.01930106,0.051410254,-0.0007526174,-0.027265063,0.04204829,-0.018335856,0.020580547,0.08301426,0.05096658,0.050870206,0.002085175,0.081955,0.01041495,0.020902557,0.064041756,-0.028001945,0.002496208,0.02693806,-0.049124528,-0.038810894,-0.06573494,-0.008373404,0.092602625,-0.043711662,-0.027484426,-0.012684615,-0.0106403185,0.015870612,0.019947233,0.0034530119,-0.05375309,0.102256365,0.04955734,0.10763653,-0.059779182,0.024533203,-0.012279607,-0.07857729,0.0129365055,-0.028879104,0.026124889,-0.03729812,-0.009903805,0.0049550813,0.052746683,-0.009915216,-0.0134617165,-0.016311845,0.0019514577,-0.06819201,0.018963957,0.052644312,0.014757655,0.051353343,-0.028560517,-0.008361422,0.03418123,0.027972404,-0.0600476,0.022853157,0.05020458,-0.025791986,-0.027926747,0.06581042,-0.05462674,0.123018615,0.061110165,-0.108880796,-0.01273059,-0.00394576,-0.045633387,-0.059001245,0.06309934,0.07001657,0.01514156,0.077978216,0.08930227,0.06008472,0.0019688914,-0.020204706,-0.056632556,0.055414833,-0.082859136,0.05144825,0.0052704215,-0.049662314,-0.054881696,-0.03906461,-0.028302826,0.0568833,-0.07236452,0.009234726,0.032282345,-0.031634077,-0.029021995,0.050995994,0.06042413,0.041837305,-0.028710578,-0.08711774,0.013792242,0.07081135,-0.043653537,0.050288044,0.094038144,-0.013552996,-0.031742807,0.042269994,-0.035351835,-0.049392223,0.07004102,-0.043098405,0.09338701,-0.03554831,-0.035827976,-0.0004810073,0.031400595,-0.06302722,-0.04903484,-0.008516072,-0.02230697,0.069893844,-0.027677923,0.0013912703,-0.00869237,0.02603895,0.0006142408,0.075171486,-0.0063525005,0.03882755,-0.06360076,0.005570232,0.029100927,0.0049879993,0.052770104,0.004772951,0.0051289666,0.031367958,0.019556096,0.016610114,0.023309784,0.0130790295,0.04525968,0.0021549813,0.0285357,-0.090187855,-0.012203215,0.07081588,-0.0797243,0.0011209849,0.089109644,0.028963346,-0.018291857,0.04310931,-0.025614733,0.032600164,0.03606655,0.035895046,-0.011502599,0.014730137,0.05550056,0.03208128,-0.056305557,0.06434442,0.09498742,-0.033958983,0.021892434,0.005064708,0.033350714,0.03521762,0.010574511,0.020084308,-0.034031052,0.016826065,-0.017468808,-0.020784955,0.0027491462,-0.07930649,-0.032292884,0.0018735522,-0.0012809634,-0.03348335,0.0032765758,0.028611904,0.050034333,0.0117425015,0.04107871,0.036060188,0.0064824237,0.0025732366,-0.016821204,0.030572738,0.040563248,-0.003718943,-0.10089665,0.012229513,0.03669697,-0.014749632,0.019634392,-0.006484832,-0.122711346,0.0026115584,-0.0027928273,-0.018082585,0.03780205,-0.027916947,-0.010486797,0.0057074903,-0.043636642,0.03808116,0.034329895,0.0009908306,0.09416905,-0.0017839706,0.013186988,-0.0049415748,0.05371935,-0.033643678,0.04453152,0.0007891076,-0.052796185,-0.009636643,-0.1006915,0.03678659,0.03009664,0.01454656,0.08240042,0.0058312663,-0.033253793,-0.053447567,0.059335697,0.032864325,0.050727304,-0.049280602,-0.02008722,-0.002296623,-0.013029645,-0.0680298,-0.01389703,0.0077717057,-0.01322416,0.054367512,-0.03509041,0.09943698,-0.052036557,0.05775197,0.02155143,0.04668494,-0.042772748,-0.029058663,-0.034618624,0.020129694,0.041520912,0.011995604,0.042532858,0.0025630936,0.052313983,0.060705934,-0.022476962,0.04436213,0.0686451,0.04333869,0.01652198,-0.05902487,0.011966063,0.037799485,0.022074673,0.028484903,0.051281676,0.029514318,-0.027206369,0.030384544,0.008648673,-0.045297205,-0.07777549,-0.025177287,-1.580378e-05,-0.030469177,-0.0008199654,-0.00040037412,-0.03812124,-0.03674415,-0.0077306526,0.012194236,0.022215143,0.0706016,0.00931302,0.055722628,-0.058535293,0.07721845,-0.08260528,-0.026509902,-0.038135502,0.015071295,-0.03600254,-0.024762308,-0.039694656,-0.04944352,-0.05262203,-0.032629997,-0.020344429,0.037021797,-0.0744358,0.067456834,-0.012817964,0.047785256,0.0019947311,0.02510387,-0.010229081,0.08642369,0.06896731,-0.029576892,-0.008415864,0.040022787,0.050064325,-0.0033591776,-0.021713184,-0.03304534,0.005293375,0.024726992,-0.0014824377,-0.04377327,0.027393792,-0.027978906,0.02530063,0.01355535,-0.03633686,-0.004316736,0.05091495,0.043968007,-0.013895042,-0.02952244,0.07240346,0.07685872,-0.017030815,0.085756905,0.01873756,0.030003514,0.008838166,-0.057422902,0.041217387,-0.06351912,-0.0700531,0.0025238753,0.01785906,-0.06486955,0.0017442703,0.021724937,-0.032255,-0.036187533,0.0069329715,-0.013343043,-0.0053220075,0.022307597,-0.03451276,0.084013976,-0.010874559,0.016549703,0.0071755527,-0.012102243,0.012906919,-0.064401954,0.039100435,0.028431553,0.029918911,-0.010313375,0.018286534,0.03345135,-0.0144640375,0.0688238,0.10459043,0.007084841,0.018567571,0.047308657,0.01973174,-0.004810819,0.04501826,0.02917498,-0.043725707,-0.034772974,0.06443521,0.029103173,0.050840024,0.02360887,0.029624542,-0.01092969,-0.033539068,0.01117935,0.029670171,-0.113612175,0.10407572,0.056186832,0.018251635,0.05987034,-0.017020062,0.07523759,0.0071226186,-0.090630725,-0.044771712,0.06776944,0.075313896,-0.0696031,-0.01679006,0.0055844192,-0.015119439,0.034608882,0.08949291,-0.057655305,0.0427169,0.0032757672,0.02015824,0.012052362,-0.006864577,-0.0058603217,0.0015434197,-0.063745074,-0.0452093,0.06754131,-0.008184234,0.03002202,-0.034202043,-0.07016995,0.033897024,0.01584845]	\N
22	security_officer	10	2025-12-04 07:21:45.805589	[0.04004419,-0.010580882,-0.025989141,0.076768935,0.009417397,0.03144276,-0.021725027,-0.02818146,-0.019267857,0.08456864,0.025060406,0.05613281,-0.01752568,0.011529415,-0.06494184,0.011982022,0.060781196,0.108322434,-0.04557763,0.042107634,-0.031252574,-0.033015218,0.015522062,-0.052641556,-0.029218197,-0.033323217,0.00434076,0.029586589,-0.03692271,-0.015747251,-0.0062222416,0.007896879,-0.045044873,0.08043941,-0.048779532,-0.067098774,0.0020649834,-0.08701892,-0.10712919,0.027223328,-0.03835053,-0.014859368,-0.018689781,0.027484916,0.014118882,0.042733606,0.0435733,-0.001176259,0.033614587,0.01143091,0.017636321,-0.0570601,0.08496246,0.060684107,0.012078179,-0.06399295,-0.0856089,0.053906627,-0.0016868433,-0.008987091,0.013682187,0.030778095,-0.017906243,0.024671542,0.01524131,0.012421145,0.027896011,0.016062152,0.057010595,0.020989746,-0.018955909,0.010092499,-0.0106824655,0.074195266,0.017020976,-0.018104805,-0.01886306,0.0027902662,0.04058357,-0.016454076,0.0026288542,0.0067588966,0.049068272,-0.028685726,-0.05591265,0.08277058,0.008222435,-0.02853399,-0.007773635,-0.0062457183,7.279322e-05,0.036768243,-0.008787147,0.0057470743,-0.004753146,0.10705912,0.09272466,0.04725762,0.0031514266,0.07642893,-0.02061941,0.020372285,-0.013634133,-0.03791589,-0.04353848,-0.0024471171,0.0019573446,-0.062351096,-0.076750875,-0.001574334,0.047390472,-0.071299136,-0.016639324,-0.00020367687,-0.02944213,0.02677966,0.056111157,-0.0150277885,-0.02580871,0.06983555,0.036219954,0.0705205,-0.020061089,-0.0061582574,-0.011129885,-0.060309213,0.004987918,-0.0076877954,-0.01981682,-0.051403962,-0.034549944,-0.040592313,0.0031856704,0.017636757,-0.03665503,-0.04801831,-0.04817789,-0.07696733,0.028950088,0.05266322,0.028442793,0.04823334,-0.011720138,0.038621105,0.019911718,0.030146766,-0.029966347,0.009144706,0.030519461,0.02590153,-0.009782299,0.017931009,-0.06049093,0.10910513,0.015789188,-0.066871725,-0.059733097,-0.007835936,-0.07525155,-0.04307813,0.020535069,0.0913013,0.0023505394,0.08464251,0.0072470317,0.056764767,-0.054308485,-0.023309175,-0.008963751,0.055700757,-0.04033691,0.054780126,-0.014861916,0.068719536,0.0057772594,0.031869445,0.003313055,0.12684456,-0.061137617,-0.0077560227,-0.006987105,0.016715392,0.013892116,0.05350159,0.060511347,-0.018873235,0.036718935,-0.036308594,0.097653314,0.030934904,0.0149650425,0.049227454,0.022454133,0.0027511974,-0.056935824,0.04529084,-0.03414671,0.012066989,0.040074613,-0.0033193468,0.08557442,-0.004978616,-0.015255583,0.025287312,0.08396613,-0.050638113,0.0042836256,0.0515227,-0.015595482,0.037160635,-0.031766284,-0.020256098,0.04609247,0.049007773,0.0028004209,0.075212546,0.0058058784,0.0379816,-0.088489905,0.06586838,0.011106606,-0.009311633,0.06084393,-0.008017404,-0.0005735537,0.063494354,0.019912284,0.012394951,0.022360904,0.029613517,0.06964118,0.0065834816,0.02105814,-0.0850685,-0.018062249,0.035766043,-0.048545267,0.029861769,0.049982958,0.041993905,0.011368905,0.05818223,-0.018226719,0.049008064,0.013377489,0.013377959,0.06051809,-0.0047967164,0.0742678,0.036487605,-0.06704726,0.017123956,0.107559,-0.0048072515,-0.011843235,0.0013877681,-0.009631854,0.008772161,-0.02759267,0.03969708,-0.004470131,0.060205497,-0.01610201,-0.06544803,-0.048610203,-0.074162185,-0.04148766,-0.0058397423,0.0045111477,-0.09140165,0.024639523,0.005198576,0.025741734,0.012981566,0.020623077,0.027742635,-0.014487777,-0.02909543,0.035630602,0.04815869,0.018971225,0.014548723,-0.12676117,0.04111396,-0.0065602697,-0.02894332,-0.02009858,0.05013677,-0.080606095,0.04202016,-0.07824002,0.009277352,0.03460111,0.025256308,0.04598352,-0.045394257,-0.053476453,0.055734713,0.0061290218,-0.045638368,0.06729198,-0.0058840755,0.020313945,0.0942868,0.08022589,0.019530209,0.015468211,-0.024179181,-0.041073218,0.024515215,-0.009967126,0.09335265,0.013698016,0.015070351,0.10161911,0.017495034,-0.030723399,0.029774465,0.077845685,0.0055515487,0.09106801,-0.053766813,0.044361774,0.0399308,-0.011534399,-0.026972419,-0.039720908,-0.030507496,-0.029612051,0.016176533,0.010783014,0.046535525,-0.022497814,-0.010011529,0.022306181,0.120858856,0.03375402,-0.023172418,-0.017741308,-0.012631208,0.029776229,0.038114406,0.028349651,-0.07542829,0.030853799,0.012281688,-0.07512196,0.0668859,0.046755258,0.00424598,-0.0056539397,-0.023729512,0.00047887507,0.038682345,0.016719978,0.0186829,0.06323786,0.036616914,-0.0039817374,0.06162963,-0.047566473,-0.036674682,-0.00368191,-0.01329202,-0.017578844,-0.02780062,-0.054967165,0.018457368,0.015595598,-0.00045839103,0.008307098,0.047046345,-0.015165747,0.03507442,-0.062329166,0.075226255,-0.038915414,0.07586929,-0.038433876,-0.020455036,-0.014237253,0.039775662,0.0118977,-0.040300954,0.0070539205,-0.011909398,-0.044339374,-0.0075854952,-0.011636999,0.03330577,-0.080102414,0.063240565,0.016830789,0.053627253,-0.06178196,0.016059073,-0.009076388,0.023914369,0.09740598,-0.037952144,0.043240253,0.015239181,0.021732984,-0.0036601422,0.040747304,-0.09948351,0.0088662,-0.01665718,-0.014340411,0.031624634,0.017948754,-0.060028262,0.054296475,0.033777323,0.0038189983,-0.017331412,0.061611287,-0.0056616366,-0.0019015422,-0.0274306,0.067924194,0.06661464,0.024313446,0.08786297,0.037216358,0.058732197,0.02246649,0.02150685,-0.03250434,-0.0796575,-0.027773872,-0.0031727627,-0.031184614,-0.11200367,0.063744,0.05266236,-0.032184962,-0.03638071,0.008703674,-0.04975887,-0.09336582,-0.017531328,-0.03321593,0.12375858,-0.06067133,0.010787942,0.018116422,-0.004455512,0.001480313,-0.07159555,0.047114957,0.023326164,0.0025798124,0.003138151,0.007580477,0.0008470024,-0.03176555,0.016234519,0.07445095,-0.016294561,0.03721162,0.075066626,0.01794702,0.020979438,-0.019236771,0.021777708,0.03161719,-0.06255331,0.067338206,-0.007764357,0.07782815,-0.024732111,-0.0011102475,0.02383089,-0.02949098,0.023753399,0.021549195,-0.052324686,0.0986056,0.043602128,0.017951872,0.07178099,-0.018494526,0.013308929,-0.024004495,-0.07641834,-0.049550816,0.015047663,0.01768804,-0.041733947,-0.04104441,0.026211469,-0.04732795,0.025894666,0.07691731,-0.07665933,0.009743559,0.07575875,0.028683111,0.057569176,0.009549263,0.016594918,-0.0048140045,-0.034268335,-0.014679999,0.017773401,-0.0716313,0.02205373,0.018809048,-0.046633452,-0.0075142435,0.033387855]	\N
23	security_officer	11	2025-12-04 07:24:07.95535	[0.0217414,0.027679397,-0.0071786284,0.024946488,0.001980613,0.05170199,0.013860606,-0.045840193,-0.059702516,0.08903036,0.02248594,-0.005845673,0.002772362,0.02945259,0.0058771507,0.0029435984,0.065175846,0.10617416,-0.057140592,0.062259853,0.038681626,-0.049757976,0.058811232,-0.046982616,0.0048502577,-0.013750595,-0.011968457,0.0047685113,0.016874623,-0.040419254,0.0021293536,0.037112813,-0.10408381,0.073928565,0.027259197,-0.05905353,0.042634916,-0.15197225,-0.05891152,0.0038901006,5.735676e-07,-0.02636988,-0.05250994,0.019583058,0.00987976,0.028686143,0.03519053,-0.029016592,0.045047406,0.0077622123,-0.016584128,-0.110121235,0.041320585,0.024970405,0.0016581054,-0.116857514,-0.068947524,0.014209578,0.014501542,0.041149277,0.02280773,0.048380055,-0.048875585,0.030736169,-0.0048520714,-0.046698418,0.032148384,0.0078256205,0.028317107,0.010647535,-0.045981053,0.020584222,-0.021070652,0.060516056,0.057027016,-0.023276245,-0.0036322633,0.01478415,0.027627174,-0.045362204,-0.006330258,-0.0625906,0.00326089,-0.030582977,-0.055299792,0.029411063,0.003991967,0.026259003,-0.015668022,0.015060729,0.017268566,0.0152675025,-0.03895033,0.010925982,0.046767,0.063430466,0.060567673,0.018369012,-0.032822356,0.08582712,0.019445846,0.029375268,0.0113729965,-0.011885315,-0.07130763,-0.035827704,-0.021598566,-0.065123715,-0.10603444,0.016131928,0.034757674,-0.05972022,0.029729059,-0.011438576,-0.07873773,-0.036855057,-0.0253001,-0.025119275,-0.024937341,0.0831889,0.10532958,0.0701777,-0.021574046,0.004937063,0.0016596867,-0.0376622,0.002431236,0.031054512,0.005960098,-0.049394526,-0.0041187787,-0.036798194,-0.039047476,0.0232438,0.03154158,0.0051652435,0.015678488,-0.05918601,-0.034694497,0.057943773,-0.0024158105,0.016045587,-0.011382724,0.015433448,0.0045554484,0.037138555,-0.03998879,-0.008765508,0.08457988,-0.01628701,-0.015297642,0.050121337,-0.024823008,0.043914776,0.057955086,-0.07439447,-0.08403146,0.015875263,-0.06675976,-0.028416226,-0.02443543,0.04094096,-0.023284478,0.12184886,0.025214707,0.05490614,-0.014789141,-0.036104057,-0.0063985474,-0.003051892,-0.022014122,0.042120073,-0.0023573022,0.033050694,-0.020658841,-0.018522179,-0.022756476,0.10868564,-0.06385826,0.008266144,-0.020834623,0.032559488,0.018752625,0.027577383,0.011169488,-0.02681345,0.039076105,-0.08907227,0.026977774,-0.026864324,0.0065562413,0.043048896,0.06594019,-0.004520048,-0.058866415,-0.002187365,-0.11162654,-0.025096666,0.04482792,-0.008822414,0.046704166,0.0025508816,-0.01993776,0.03763795,0.045491867,-0.044576883,-0.033775005,0.008472546,-0.019967891,0.025812116,-0.03582656,-0.022602577,0.015393653,0.036334712,0.0046799355,0.07281183,0.049920358,-0.0027371256,-0.023606682,0.062088907,0.07967513,0.034246944,0.032469094,-0.01021023,0.028928204,0.08775506,0.025823727,-0.009472411,-0.004146347,0.06263102,0.02463379,0.04068161,-0.013982424,-0.023155773,0.027496716,0.04210226,-0.03113962,-0.008886824,0.057709314,0.043526433,-0.050905004,0.05431101,-0.0070026037,0.060912285,0.038407963,-0.031339366,0.04812114,-0.019789541,0.10531975,0.036105424,-0.035859317,-0.013220061,0.043223195,-0.077127025,-0.02038191,-0.054132562,0.026094802,0.024501067,-0.023446301,0.014556943,-0.016479352,0.05625397,0.00042086947,-0.042997297,0.0082257725,-0.10395576,-0.06376935,-0.025246054,0.013955835,-0.1096556,0.06842793,-0.010186824,0.044509098,0.03896974,-0.0019917684,-0.0018990826,-0.054830603,-0.0076428377,0.017669784,0.033550076,0.018606976,0.020242076,-0.07061203,0.08381739,-0.015911706,-0.054470092,-0.007087871,-0.019397903,-0.06051748,0.041125804,-0.06352283,0.028204285,-0.0021931797,0.009544893,0.015358248,-0.015414841,-0.027120829,0.022517387,-0.08120718,-0.04386032,0.06366363,-0.02955464,-0.010107138,0.08130304,0.077013254,0.01090955,0.022257702,-0.012778425,-0.033857726,0.010522391,-0.03897424,0.027960915,-0.03244965,-0.019882496,0.0768764,-0.00072977954,-0.026239976,-0.030057697,0.049727395,-0.032984406,0.04449018,-0.045583863,-0.011227118,0.009443923,0.0080470685,-0.03977558,-0.008735652,0.007126472,-0.05726705,0.010942443,-0.025890315,0.025663419,-0.05253531,-0.039153285,0.000890604,0.055071022,0.046382707,-0.0021122657,-0.04131825,-0.015637934,-0.00048102517,-0.0008730125,0.04011303,-0.013440116,0.049252782,0.09195887,-0.012765029,0.028925316,-0.0052798726,0.02837658,0.009071839,-0.04624599,0.023131622,0.06950768,0.051930152,0.023776425,0.05115165,0.06265159,0.0009244672,0.010212222,0.010119387,-0.043280564,-0.061400115,-0.032798603,-0.011037791,-0.009768603,-0.039114513,0.022343347,-0.05593742,0.02250961,0.028917653,0.033333104,0.015217088,0.05235253,-0.06402992,0.03551702,-0.0019535148,0.06808167,-0.040867172,-0.0055882265,0.0002694677,0.01911056,0.036947787,-0.0359173,0.0298448,-0.0016751774,-0.08764249,0.023966443,-0.035046503,0.077748075,-0.051857747,0.098088756,-0.012497797,0.08767355,-0.03810681,-0.006620668,-0.05871913,0.01877145,0.030048603,-0.008083788,0.0018335743,0.006464231,0.037281465,0.03761484,-8.540684e-05,-0.07180335,0.044562787,0.01242234,0.020603307,0.037019446,0.013717711,-0.046090484,0.009239924,0.07745902,-0.020234771,-0.06447761,0.038951144,-0.03557959,0.047211092,-0.07101036,0.019924743,0.014199296,-0.024002261,0.033312526,0.071107686,0.09881293,0.06907291,-0.034538496,-0.052996628,-0.0322306,-0.012795475,0.02997577,0.03133334,-0.08294374,0.10650999,0.04424087,-0.01029285,-0.01857189,0.0027831604,-0.076512866,-0.05341458,0.0041143657,-0.024160964,0.08889346,-0.029862598,-0.008782094,0.033235762,0.016859332,0.04018935,-0.04820821,0.056207508,-0.033058666,0.016181951,0.008047273,0.03755213,0.039705805,-0.036452606,0.07093721,0.075201705,-0.009142434,0.028344788,0.11266235,0.0039536892,0.005042159,-0.012147908,0.049608864,0.017937878,-0.0409165,0.087994754,0.0126258405,0.07627568,-0.014390047,0.013989206,0.044210926,0.07047917,0.034217615,0.002402408,-0.031240266,0.034614354,0.047307298,0.029794542,0.06777411,0.018108279,0.045033317,-0.034342024,-0.05287103,-0.021159874,-0.014488795,0.06737058,-0.044765085,-0.06503675,-0.018346187,-0.06579088,0.024404187,0.053903542,-0.06386837,-0.0023767308,0.06670007,0.044152483,0.076824024,0.0023322054,-0.049931046,0.070017435,-0.060588814,-0.040801346,0.02707137,-0.05579798,0.05647047,-0.014711519,-0.05827061,-0.026784722,0.055903774]	\N
24	security_officer	12	2025-12-04 07:43:09.421409	[-0.036677074,-0.0660542,-0.10496523,0.07653201,0.030952884,0.041361436,-0.031401973,0.018117879,0.022958478,-0.045895476,-0.00920095,0.08109964,0.037763495,0.006843121,0.011417458,-0.03522763,0.039152373,0.07359898,0.031179635,-0.056002244,-0.06805092,0.04539603,0.10500966,-0.046074066,0.015577136,-0.010354022,0.0009538198,-0.030494321,0.011291901,-0.0055118334,0.020125477,0.030851595,-0.015726782,-0.014811028,-0.008021964,0.030273806,-0.020508563,-0.027664145,-0.1267987,0.073834956,-0.0049482533,-0.018160343,-0.013435728,-0.03734287,0.029176962,-0.019580355,0.0750734,0.06933865,-0.094114594,-0.057790123,0.01550701,0.053667057,0.08522561,-0.015326623,-0.08345065,0.036795344,-0.03617192,0.110841855,0.016840046,-0.024173053,0.00042808856,0.021235792,-0.02657577,-0.03147344,-0.025543068,0.07930289,-0.017210003,-0.010764371,-0.043070737,-0.014975178,0.010288152,0.019436415,0.016055204,-0.015456683,0.058497805,-0.093699016,-0.017503707,-0.027666707,-0.022382094,0.013425528,0.008459808,0.042026274,-0.00836943,-0.0076918085,-0.022068439,0.027802525,0.0114139635,0.07199933,-0.07076564,0.0122526605,0.05912492,0.022274626,0.09035677,-0.07941761,0.057784162,0.016387042,0.035389856,0.036899813,-0.05226465,0.046871636,0.03319544,-0.016411565,0.055639014,-0.017039338,0.011024707,0.02589361,0.0021033108,-0.016370332,-0.015566425,-0.0049196547,0.07613695,0.023877926,-0.07315982,-0.032635454,0.022542007,-0.026228664,0.04896253,0.014008972,-0.06580023,0.06268009,-0.058420405,0.0065485495,-0.008571677,0.038461234,-0.04463736,-0.053521127,0.0049620247,0.031137357,0.006587804,-0.085826136,0.026682816,-0.04129438,0.09641293,-0.056942683,-0.07034694,0.059258334,-0.013639093,-0.0024891614,0.07867564,0.048870172,-0.043830186,0.026107308,-0.008153506,0.06520718,0.0939093,-0.047741625,-0.07594806,0.0046295435,0.07229058,-0.0019744462,0.026251534,0.01963255,-0.03158306,0.050105225,0.06843258,-0.08834513,0.088127114,-0.007688426,0.027068324,-0.019766886,0.051022455,0.050425734,0.027032504,0.024034565,0.06231901,0.02154042,-0.07190932,-0.03933929,-0.046110995,0.017232925,-0.07251123,0.018175079,0.027409643,-0.03840537,-0.03132349,-0.019177893,-0.0011766028,-0.013115055,-0.06381152,0.042975463,-0.055892777,0.0027236245,-0.069350116,0.07463835,0.031846132,0.08042895,-4.2665088e-05,0.02258216,0.013188203,0.057232622,0.0011895573,-0.0632828,0.058745198,0.010092229,-0.0007938563,0.01961402,0.04197148,0.018913638,-0.003535766,0.01441324,0.047791645,-0.058486544,-0.04874036,-0.04684532,-0.007866203,-0.04027427,0.00035893114,-0.02950515,0.013211265,0.054228384,-0.054571897,0.013379704,-0.03502057,0.028798778,-0.036899008,0.09394306,-0.037336808,0.018411048,-0.015694382,-0.050433673,-0.046616834,-0.054706365,-0.018288836,-0.060230687,0.027366793,0.03502482,-0.026070235,-0.013433323,0.009875644,0.03518237,0.026581075,0.024081862,0.057256833,-0.03208239,-0.021687672,0.032514945,-0.01755017,-0.042956855,0.050162595,-0.06780053,-0.050061826,-0.04746526,0.026104594,-0.05979502,0.048296373,0.037368793,-0.020661676,0.0385642,0.0018916063,0.043237403,0.029069478,0.021358367,-0.003369888,-0.0070018345,0.08151571,0.019096972,0.05960761,-0.045210157,0.060229603,0.04252671,-0.019109288,-0.001092576,-0.008474251,0.010088534,-0.010694302,-0.041719608,0.0018285092,-0.0004710875,-0.012739352,0.018826352,-0.09560555,0.025692167,-0.029249603,-0.02622548,0.0091553535,-0.06822628,0.012314468,0.005283032,0.008681967,0.030840088,0.09170312,-0.0034410066,-0.0204533,-0.054003727,-0.005640295,-0.013583709,-0.0316871,0.0011575064,-0.04409515,-0.040642504,0.06591878,-0.0169477,0.08722806,-0.053612627,-0.05965758,0.023617264,0.0128982095,0.04358535,0.063757315,0.05011364,0.065300815,0.051292073,0.04238991,0.009933145,0.044286624,-0.06707024,0.00046261793,-0.050022624,-0.0377708,-0.0082653845,-0.053645298,0.057219483,0.020204805,-0.017878562,0.03963986,0.068686225,-0.006671991,0.008562989,0.030555343,0.011682623,0.08911452,-0.05933712,-0.013878539,0.05200133,0.0053182403,-0.014257603,0.016085165,0.013010207,0.07497774,0.10137193,-0.014044205,0.07567138,0.03483306,0.030703679,-0.0413195,-0.0011844095,0.0037376077,0.028009785,0.0480784,-0.016140498,0.04990649,-0.047659528,0.002054824,0.020752063,0.028169062,0.009716466,0.010282493,0.04718724,0.055898894,0.004193021,0.029549703,-0.03564541,-0.020378277,-0.037619416,0.040055096,0.0063564316,0.040242728,-0.006954394,0.010143655,0.008802426,0.024165386,-0.01719064,-0.09469476,-0.048765972,-0.0049082567,0.0013896781,0.029175026,-0.021778386,-0.028658506,-0.088727936,-0.05445437,-0.015420765,-0.016460551,0.04357389,0.06460885,0.060582187,-0.048693504,0.06304924,-0.037775457,-0.020731347,-0.10784507,0.0024256893,-0.020127311,0.00066665333,-0.028839374,-0.048930097,-0.05049319,-0.07364582,0.044863045,-0.02328219,-0.017184703,0.032136276,0.03956746,-0.027051471,0.010707213,0.007895016,0.050819546,0.06749752,0.034420483,0.04089899,-0.056196544,0.0264065,-0.039754394,-0.0007521217,-0.0180349,0.009132303,-0.010201646,-0.012098242,-0.005208314,-0.05384358,0.032543898,-0.017021593,0.035894357,-0.014494845,-0.029439384,0.039778978,0.04467181,0.048540905,-0.041497774,-0.06427667,0.050766706,0.010364463,-0.01310092,0.109609686,-0.050945885,-0.028577885,0.030623373,0.008495164,-0.00044677852,-0.07355023,-0.08636591,0.035876025,0.024989177,-0.028458435,-0.07784619,-0.04246082,0.021999434,-0.008545607,-0.06994136,-0.028833887,0.02204527,0.01689295,0.027727362,0.07938783,0.021933408,-0.008936053,-0.062467854,-0.038668834,0.015286699,-0.00823095,0.010062294,0.07211046,-0.00480922,-0.024074376,0.02288175,-0.008448189,-0.011629825,0.07324144,0.11599677,0.022600202,-0.04042764,0.010263991,-0.047659278,-0.01625788,0.06534484,-0.0023483203,-0.078612894,0.006406177,0.06509558,0.08066218,-0.009065631,0.033608496,-0.004884086,0.0015594274,-0.04461795,-0.0242755,0.010774102,-0.070751704,0.10643487,0.07411901,-0.02685063,-0.021651784,-0.0006774183,0.0018578265,0.05150514,-0.01733759,-0.028155085,0.021863837,0.057132404,-0.10397712,0.010229722,0.0036625697,-0.05166524,0.002925023,0.08403163,-0.012465727,0.027822178,0.036287647,0.05551651,0.032065153,-0.07074374,-0.0016551598,-0.031115988,0.031889994,-0.049480088,0.048701297,0.069409154,-0.058176756,-0.010491306,-0.011067768,0.016169,-0.01694639]	\N
26	ADMIN	17	2025-12-05 04:59:24.939055	[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]	photo_2025-12-01_11-04-00.jpg
27	ADMIN	18	2025-12-05 04:59:54.877286	[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]	photo_2025-12-01_11-04-00.jpg
28	security_officer	13	2025-12-08 01:46:54.665745	[0.039267194,0.0034443215,-0.021576282,0.04077624,-0.06958267,0.06144417,-0.058482196,0.001218234,-0.04468265,0.074003845,-0.004954887,0.044330906,-0.004101586,0.011259164,0.011696822,0.0106866015,0.07486994,0.073399335,-0.04178021,0.03135078,-0.009288562,-0.043435484,0.018103272,0.03423123,0.03790362,0.00018429637,-0.03183396,0.0692581,-0.03450418,-0.008988865,-0.0063433205,0.06716435,-0.02972789,0.04506904,-0.023660537,-0.056480963,-0.03142264,-0.09840056,-0.038689606,-0.0162578,-0.020103943,-0.012749326,-0.05776979,-0.036019813,0.037652172,0.0459755,0.05766278,-0.06616991,0.10613299,0.0039681382,-0.009443524,-0.03738221,0.07046459,0.03566643,0.00079188263,-0.020773474,-0.08459012,0.07126168,0.038902823,0.031588197,-0.022582438,0.019293256,-0.046483785,0.038504243,0.019562071,0.047058813,0.0153524745,-0.0037188944,0.044373117,0.03412259,-0.020814985,0.0090830065,-0.0034504062,0.11713649,0.0024759062,0.029425083,-0.060498465,0.0064175786,0.04012952,0.004325893,0.034796976,-0.025263691,0.014474186,-0.008782658,-0.0054682223,0.008516131,-0.0014433466,0.051654253,-0.005762693,0.009625882,-0.03386949,0.043143984,0.033871353,0.023623891,0.0070618377,0.0732541,0.027745008,0.01410958,0.03499158,0.068671025,-0.014984966,0.040658895,0.001447723,-0.05914997,0.03238535,-0.006996553,-0.014619497,-0.07753389,-0.06346326,-0.025309294,-0.00021782445,-0.07388937,-0.040479857,-0.019961437,-0.06236324,0.024882218,0.02250235,-0.044466797,-0.07496417,0.04875765,0.013813429,0.046435,-0.017372688,0.014440244,0.048342448,-0.026027666,0.03602128,-0.00067959755,-0.018690482,-0.09908331,-0.027015775,-0.03890749,-0.0005781159,-0.011987428,0.00029574506,-0.013960485,0.0077535743,-0.029990869,0.0030099251,0.008063679,0.027615592,0.00019872539,-0.0018704624,-0.012809379,0.03349967,0.00033801552,-0.09502041,0.010159983,0.06126822,0.026998146,-0.021162052,0.031628046,0.017977,0.107834294,0.004821436,-0.034293048,-0.012835518,-0.028169079,-0.056098215,-0.069020525,0.0005213892,0.0770173,0.008741233,0.07160913,0.037349906,-0.028868021,-0.021465328,-0.0045006922,0.02796371,0.048278388,-0.057002738,0.05735124,-0.04906033,0.0016083128,-0.060901564,-0.012813984,-0.0018172293,0.09848578,-0.054078862,-0.0023563164,-0.039647005,0.0066122003,0.032347854,0.08165581,0.046376485,-0.05162789,0.024999382,-0.035832074,0.012328121,0.008403414,0.025659308,0.05087197,0.04975183,-0.005649433,-0.054650195,0.04697696,-0.005569773,-0.07510363,0.061228227,0.00011435944,0.09033026,0.07466998,0.00097556954,0.057759747,0.06957591,-0.06527894,-0.06539244,0.011752942,-0.053128384,0.065332495,-0.024965499,0.01762104,-0.011726163,0.039770596,0.014142351,0.09131635,0.040971775,0.01851693,-0.05037653,0.008500343,0.033636916,0.081450656,0.030245207,-0.011559083,0.01353092,0.030757012,0.014357618,0.07034131,0.021142911,0.08828677,0.060965206,-0.06398921,0.009928042,-0.05781081,0.016861647,0.041303385,-0.015596521,0.019345399,0.03533044,0.0026116078,-0.0076388866,0.0985594,0.03245233,0.041898355,0.049739286,0.010250412,0.0062975544,-0.008368674,0.09663833,0.015208276,-0.03774476,0.021497734,0.074852906,0.021409297,0.016314575,-0.0015701884,0.038183015,0.024569966,-0.013350465,0.051082514,0.0016869787,0.001676795,0.015409253,-0.06027402,-0.0052765524,-0.12676439,-0.03986386,0.031015454,0.009996909,-0.03596564,-0.026766669,-0.03572665,0.016440846,0.06343263,0.0042607924,-0.010046016,-0.09103881,-0.036093775,-0.013454485,0.044164814,-0.0069683427,0.0047951695,-0.1259387,0.040641703,0.023581011,0.012053645,0.002105994,0.00887784,-0.12218565,-0.009443177,-0.034997463,0.08679321,0.07480664,-0.012227368,0.015214576,-0.035825517,0.013551246,0.034692384,-0.028300999,0.0067033656,0.07762092,-0.061119832,0.0176527,0.06817471,0.061429214,0.009545232,0.008667154,-0.038927335,-0.011095766,-0.049741115,-0.057662252,0.01261915,-0.03452029,-0.02388057,0.03527635,0.012231441,-0.04127568,0.002755883,0.058616277,-0.031749453,0.034170724,-0.081405275,-0.013624147,-0.005980701,-0.016815295,-0.019074727,-0.041078612,-0.044483066,-0.04725965,0.04469135,0.0061007887,0.052373707,-0.023263918,-0.05838725,0.048114255,0.100631274,0.0027571674,0.0014570412,-0.013917456,-0.034318216,0.021021273,0.01620565,0.03101939,-0.06929338,0.040469144,0.018968413,0.037345104,0.07688382,0.02810898,0.08671268,0.049902994,-0.021777704,-0.061282396,0.05341067,0.046917863,0.049805082,0.034158632,0.012040964,-0.007091059,0.03869179,-0.043472268,-0.04102142,0.0029217957,-0.04170743,-0.015419507,-0.007946076,-0.0030643265,0.006322552,-0.031792525,0.04280833,0.013547843,0.07505273,0.022443376,0.005989892,0.019850314,0.05480859,-0.02655286,0.055396482,-0.015433938,-0.0012907076,-0.05141503,0.032665297,0.018395824,-0.0048321728,0.024312332,-0.043485045,-0.031215174,-0.018907834,-0.018344652,0.06550114,-0.08116426,0.053452797,0.026901599,0.002103582,-0.022772998,0.018004654,-0.02767571,-0.043796826,0.018658165,0.021720804,0.026054766,-0.01628052,0.03339837,-0.023227891,-0.036160108,-0.10005624,0.086944796,0.028876932,-0.032813556,0.0023113037,0.044286404,-0.08937895,0.062151864,0.026184699,-0.05329651,0.019129744,0.049074028,-0.022023635,-0.013912772,-0.0082485415,0.081546925,0.026950987,-0.009564519,0.09921924,0.048694026,0.007926216,0.035062063,-0.004146096,-0.015771,-0.107089445,0.022160238,-0.014961478,0.015171515,-0.09706696,0.076222725,0.049587548,-0.005851913,-0.030657837,0.016748428,-0.09168364,-0.05473657,0.0022779815,-0.0033560668,0.09780165,-0.016307529,0.015089237,0.02830766,0.025996856,0.0076833693,-0.018979441,0.072003104,-0.0062626028,0.083884366,0.00724855,0.037767015,0.0014237465,0.0017093798,0.05610175,0.077770606,-0.0024900683,-0.060814127,0.035044573,-0.011378097,-0.026146967,0.020853879,0.036362723,-0.037979655,-0.05474183,0.085340805,-0.0006456362,0.004449284,-0.013429489,-0.01523207,0.022708934,0.038443223,0.011204247,-0.05338014,-0.074275166,0.09621097,0.061945815,0.04613447,0.036132608,-0.017131276,0.0040795696,0.01597537,-0.13500707,-0.024494164,-0.0081461165,0.0859994,-0.045019392,-0.06414212,0.025724316,-0.04224207,0.05533089,0.02806705,-0.079662666,0.022388363,0.038871743,0.008314926,0.028913883,0.011622265,0.029853746,-0.019489126,0.0065824166,-0.03881957,-0.055825967,-0.08545652,0.033196706,0.036361013,0.005384186,-0.022086779,0.03113078]	\N
29	security_officer	14	2025-12-08 01:47:08.722542	[0.101123214,-0.024960112,-0.011321621,0.06338747,-0.06736808,0.0306266,-0.104443505,0.018615406,-0.04245487,0.03843535,0.067571506,0.06011289,-0.014805995,-0.022513367,0.00057750015,-0.053592693,0.046215873,0.087191336,-0.010557911,0.0032580255,-0.016304996,0.050164305,0.047420442,-0.0902646,-0.1081399,0.02342117,0.029775007,0.037181932,-0.01299232,-0.020100398,-0.00079755584,0.056648847,0.059865538,-0.021499539,-0.04238642,-0.074708365,-0.012403286,-0.012196963,0.042796556,-0.053226434,-0.083894245,0.008025264,-0.0071482332,-0.057052743,0.012350141,0.02002459,0.0056693153,-0.055223007,-0.007967685,-0.0041034506,-0.03049977,0.030640827,0.024583196,-0.0055174404,-0.065809265,-0.0054364083,0.025588831,0.06292993,-0.012841588,0.075866796,-0.07641667,0.05737637,-0.08099109,0.034427036,0.002162793,0.044037722,0.02497351,-0.03556505,0.04039167,-0.036433544,0.028945293,0.03685661,0.042064495,0.05681593,-0.016918346,-0.051622722,-0.06539809,-0.046546984,-0.056130458,-0.018353501,-0.0083657475,-0.012032774,0.05670633,-0.032698862,0.013582037,-0.024544964,-0.012954218,0.031085417,-0.07342585,0.009497122,-0.05422167,-0.031031229,0.036275543,-0.027330529,-0.032470997,0.07612776,0.00862718,0.018375656,-0.05087904,0.02935408,-0.016790064,0.056855913,0.01644587,0.021152858,0.07537203,-0.049843397,-0.0050854497,-0.08592912,-0.039384957,-0.06360798,0.059422296,0.0010087888,-0.10572662,-0.01515947,0.008671848,0.050063647,0.07108597,-0.0060431827,0.07203673,0.07272212,-0.03927872,0.018661205,-0.04815588,-0.025145777,-0.02133396,-0.039539527,0.026372286,-0.022222467,-0.009642217,-0.09945443,-0.04321962,0.0029375176,0.012838467,-0.007303565,-0.075554505,0.032432538,-0.100638784,-0.023488339,0.05909407,0.027135948,0.016329015,0.0724063,-0.03956552,0.0058631175,-0.0062503074,-0.013435371,-0.09094302,-0.03436311,0.04578048,0.11700769,0.052050594,0.04828799,-0.026892543,0.044629924,0.10656104,0.039853107,-0.028742013,-0.005271864,-0.028628116,-0.094014674,0.0338245,0.040052593,-0.023114085,0.039238065,0.051437005,-0.012646755,0.027246447,-0.005717015,-0.035853513,0.10792498,-0.06811518,0.062336437,-0.06615096,-0.058831964,-0.029669821,-0.048684847,-0.01680465,0.011759512,0.02369063,0.007486086,0.009805434,-0.040443204,0.008162131,0.0032328204,0.03231774,-0.012868816,-0.013628896,0.021399844,0.025230976,0.04362074,0.018166488,0.042871255,0.044690304,-0.0048305113,0.043074243,0.047409043,-0.014983699,0.004900138,0.052310254,0.00087664684,0.06143349,0.049495097,-0.031189267,0.009917136,0.010813695,0.045042716,-0.077681646,-0.041099556,-0.054215893,0.05337631,0.026651712,0.014514539,-0.0009534049,0.033118173,-0.012616639,0.0014453462,0.028359935,0.004656584,-0.012198421,0.040337265,0.030037845,0.036835477,0.04554474,-0.043762248,0.034015384,-0.025935337,-0.010134604,0.045977946,0.024749376,0.08493405,0.11632517,0.010053246,0.0055323495,-0.07340273,-0.030526012,-0.013877986,0.0024572813,0.004013641,0.06314101,-0.04125704,0.028443635,0.034142636,0.076075956,0.010386365,-0.0023338597,0.039700966,-0.049569238,0.012942243,0.024590325,0.0078549525,-0.06689544,-0.04108952,0.09026541,0.051855132,0.0067686234,-0.029109832,0.028524537,0.011266756,0.058618058,0.014567044,-0.0036846073,-0.0025099912,0.014312408,-0.024792906,-0.03184031,-0.07690725,0.010152338,-0.038891826,-0.0012981328,-0.0314887,0.01489426,0.072901614,0.11831642,0.0019267498,0.01973905,0.03510667,-0.061278887,-0.029797448,-0.025782824,0.0037344326,-0.0151396,0.08003557,-0.10622236,-0.065057114,-0.0645208,0.022427786,0.071260534,-0.0071586287,-0.06155379,-0.032931726,-0.043551024,-0.027930358,0.0075446363,0.032856915,-0.0323705,-0.0790957,0.00610505,0.016324077,0.015977673,-0.0065517393,0.054172453,-0.0532867,-0.009742364,0.0078991335,-0.025230238,-0.05373511,-0.023776073,0.0019862845,-0.03842267,-0.013693463,0.008400101,-0.013520809,-0.048725672,-0.030161548,0.051607147,0.034600563,0.0037203005,-0.04826724,0.07667365,0.00603483,0.074683405,-0.04923016,-0.03914156,0.033217166,0.047158323,-0.03438662,0.02076181,0.0010114427,0.0424024,-0.0006845544,0.04139444,0.015924444,-0.022983992,0.02262644,0.025483808,0.10093104,-0.036371823,-0.07614464,-0.03444753,-0.027975004,0.06529503,-0.027087912,0.0338283,-0.022521133,0.02298963,-0.010690767,0.011973637,-6.0328133e-05,0.07458072,0.062976904,-0.016156463,-0.028939784,-0.054960117,0.06955685,0.0131991785,0.016288092,0.039600912,0.049683545,-0.08218801,0.069778465,-0.0185139,-0.022283552,-0.05278916,-0.030873612,-0.017448613,-0.012412516,0.024800587,0.005556927,-0.03944243,0.024118232,-0.03892864,0.035056975,-0.04002864,0.0029993174,0.027910627,0.044144023,0.0077016107,0.05213144,-0.037561953,-0.032445636,-0.11240128,-0.005078066,-0.0199892,-0.010125715,0.048162308,-0.058811,0.007415332,-0.053908117,-0.029994128,-0.011396422,-0.0035054164,0.07743919,-0.011685069,-0.055477574,0.049285114,0.087079994,0.03018962,0.021357108,0.005176083,0.013513245,0.007312463,-0.013869706,0.00224163,0.06321802,0.010751666,-0.09496397,-0.034505717,0.0040951003,-0.0391905,-0.010550658,0.068506286,-0.06457493,0.047922246,0.069209576,-0.05616848,0.013992897,0.04400843,0.05631271,-0.021043276,-0.016641796,0.06721084,0.043153208,-0.0070026293,0.0053988285,-0.034338277,-0.0017001218,0.003137379,0.0009155781,0.014806081,-0.027797328,-0.0201323,0.026052002,-0.014006497,-0.054887116,-0.03177666,0.018724576,-0.016988263,-0.03814205,0.03186488,-0.04882915,-0.0053313654,0.084928855,0.0043582227,-0.009120453,-0.019528594,-0.009196068,-0.00039467053,0.024879234,-0.07344952,-0.05914399,0.011538868,0.06830125,0.076564826,0.038211755,-0.0017583851,-0.008911326,0.010002986,0.06428216,0.07523225,0.089508,-0.017258117,0.005092273,0.022937117,-0.065406896,0.006131272,0.01962526,-0.009793793,-0.014108863,0.048136663,-0.0073538977,0.054352313,-0.03356348,0.11252063,-0.043384977,-0.026890038,-0.028869247,0.01897142,-0.11686648,0.043353952,0.03657905,0.05115059,0.040873773,0.05944235,-0.009034356,0.0029635162,-0.033579703,-0.065265484,0.024283176,0.01960314,-0.033939507,-0.024654722,0.0041656042,-0.045418445,-0.012870946,0.10339686,-0.06069925,0.04824415,-0.0077942363,-0.011461287,-0.038570598,-0.0119482055,0.06515621,-0.047944844,0.04308167,0.01476258,-0.026274478,-0.033320617,0.02697926,-0.015534045,0.010064419,-0.033391163,0.003070853]	\N
30	security_officer	15	2025-12-10 00:31:27.242796	[0.08513258,-0.002201168,-0.01913047,0.06263002,-0.0029985572,0.07939537,-0.10448469,0.029517628,0.025390567,-0.007770745,-0.008033007,0.03776349,-0.0032998875,-0.04811313,0.0042944057,-0.005147134,0.051772967,0.04442562,-0.028798888,-0.03603233,-0.06561561,-0.010933453,0.03849338,-0.034381114,-0.045054536,0.047980826,0.02515437,0.04762958,-0.03569764,-0.013122433,-0.009935094,0.050621837,0.0042999713,0.014831124,-0.01623546,-0.016036265,0.07438628,-0.023764348,-0.08816558,-0.012756374,0.039791085,0.0155775305,-0.0011609842,-0.055387124,-0.0029244062,-0.03276597,0.043693,-0.012379349,-0.04617901,-0.070385695,-0.0075575346,0.044420227,0.015324258,-0.018968072,-0.05725942,0.05229023,-0.027422734,0.03207373,0.064159736,0.015049261,-0.04142806,0.0413046,-0.10290472,-0.014572818,-0.01516552,0.07950207,0.061824247,0.0025948673,0.061629485,-0.026604857,0.02655397,-0.013796779,-0.011706255,0.049048454,0.03831125,-0.063928,-0.08550328,0.00010941419,-0.041949492,-0.0028287666,0.03753074,0.00389349,0.048092578,0.0033758443,-0.014220348,0.042878415,-0.018478999,0.05306225,-0.06070108,0.014832144,-0.03890829,0.0041463855,0.066469975,-0.024888305,-0.0249095,0.07096577,0.041395754,0.011514082,-0.010382591,0.017509658,-0.044668246,0.022593806,-0.03962033,0.0021217372,0.025783664,0.0064302804,0.030220775,-0.124441825,-0.027295768,-0.017156092,0.0480783,-0.020034341,-0.11644415,0.009914991,0.013272897,0.058751054,0.10156811,-0.050113004,0.021844786,0.073315464,-0.03557044,0.03359532,-0.044978224,-0.017594803,0.0057020383,-0.0726841,0.05582127,-0.016508475,-0.043793023,-0.08166027,-0.03586791,0.00403911,0.057708822,-0.041175395,-0.07285404,0.009283964,-0.05909508,-0.113838956,0.074328706,0.020413453,0.019915327,-0.009727326,-0.016577087,0.071593285,0.057622433,-0.08430096,-0.0832869,-0.010950231,0.06710631,0.026915342,0.02718478,-0.004557691,0.021754974,0.07202231,0.045695335,-0.009993791,0.032345325,-0.02116674,0.0030039519,-0.070969954,0.078300126,0.074745834,-0.014888044,0.014713057,0.042739615,0.041837644,-0.051690478,-0.033498842,0.0051058084,0.09593469,-0.03917309,0.08930694,-0.06796708,0.0055843433,0.022995032,-0.015739022,0.041766427,0.035862923,-0.044153817,-0.003829498,-0.003785584,0.01778311,-0.02968889,0.048790354,0.059090298,0.025760254,-0.047474787,0.06518338,0.12598354,0.0763458,0.019545987,0.050079867,-0.0050482964,-0.041956663,0.014042399,0.052493602,0.07850474,0.0327127,0.036100693,0.012432584,0.047642805,-0.03204693,0.025773797,0.011649679,0.020936338,0.026375325,-0.048429336,0.051492974,-0.015875338,0.100064665,-0.026145952,-0.0058168154,0.02844464,0.04723899,0.01271896,0.04749388,-0.034750845,0.011580267,-0.109299354,0.02307804,-0.013129742,-0.045977872,-0.03232099,-0.037025236,-0.06076109,0.03014591,-0.027753226,-0.003817763,0.033281885,0.032345567,0.060794886,-0.01539687,0.015375624,-0.112352215,0.0016984481,0.009128978,0.02467716,0.016077258,0.031513087,-0.037462227,0.05309866,0.078166455,0.055471618,-0.014767109,-0.021678727,0.0485334,0.05155687,0.034476995,-0.03063037,0.029549804,-0.017897587,-0.004857746,0.11737363,0.00047502658,0.029853467,0.002930257,0.029523574,-0.016078709,0.03882773,0.027471846,0.026389902,0.017806647,0.0028137884,-0.07985486,-0.026150601,-0.05625725,-0.0063148304,0.036720287,-0.03019546,-0.06694066,-0.03668345,0.06754874,0.046503924,-0.0526873,0.0142362295,-0.024389228,-0.067885354,-0.04418916,0.034871046,0.042385597,-0.020128528,0.047907114,-0.07814306,-0.0038019274,-0.04317798,-0.023035066,0.018846354,0.057785735,-0.008482134,-0.020198049,-0.027943205,-0.0072910185,0.017634993,0.0525299,0.020917507,-0.025159515,0.022761201,0.0668883,0.048314746,-0.005018009,0.026469039,-0.070071585,-0.0050708284,0.03280437,-0.00522185,-0.037286628,0.018983724,-0.046679065,0.0048363116,-0.014782623,0.0016623263,0.03220734,-0.037974034,-0.04290537,0.03049629,0.04336145,0.012513556,0.056925554,0.07094624,-0.0105381,0.1096951,-0.08820863,0.006671529,0.06403797,-0.05668195,-0.035455085,-0.01360828,0.0031270066,0.0333558,0.038154546,0.02947731,0.01010939,0.038888853,-0.029178126,0.010989254,0.10607574,-0.00527402,-0.034303673,0.055225357,-0.013878445,0.02654958,-0.045326356,-0.039666858,-0.036223784,-0.013830548,-0.081114225,0.014489125,0.061061103,0.037566606,0.03473245,-0.010025815,0.020213857,-0.02257314,0.03602628,0.008685154,-0.006821007,0.044234086,0.015407729,-0.048837256,0.087626815,-0.032766867,0.011052601,-0.042272445,-0.086762734,-0.05714465,0.032912523,0.0018798315,-0.004929511,0.05060373,0.03548459,0.0022123812,-0.002462051,-0.048497554,0.0035943792,0.007618753,0.033972975,0.017644783,0.03413416,0.02019145,-0.014237383,-0.11343484,-0.010866446,-0.004626454,0.009535833,0.03249309,-0.038800295,0.0061492315,-0.048785005,0.07014094,-0.061128188,-0.06794031,0.09028414,0.018937474,-0.00032795954,-0.037776776,0.051625807,0.07370442,0.053528905,0.02726317,-0.026023168,0.008608598,0.025018236,-0.023145005,0.028325174,0.0067570177,-0.092649415,-0.01761051,-0.03773652,-0.00097501406,0.033268083,0.09396887,-0.099335805,0.09068732,0.021262096,-0.028218204,0.05554122,0.041696716,-0.01619971,-0.03298866,-0.0061918716,0.07436616,0.06776139,0.014764994,0.06941529,-0.062287666,-0.01021193,-0.0525632,-0.008736201,-0.02352311,-0.07156821,-0.024418436,0.01603983,-0.031723913,-0.045951374,-0.0054107863,0.03448945,0.009458052,0.022991545,0.003915715,-0.034071654,-0.03515382,0.069778524,0.0069031473,0.055644616,0.011418573,0.0073053506,-0.012985371,-0.031303048,-0.019476704,-0.022416752,-0.026874267,0.030996146,0.048241477,-0.019913074,0.017095651,0.013087404,0.010215055,0.04942905,0.06520466,0.0068560094,0.038043924,0.04647881,0.01492495,-0.06271385,9.0180394e-05,-0.048374385,-0.039800588,-0.046593416,0.057797555,0.018836953,0.06615829,-0.020429267,-0.014711362,0.006284746,0.020119734,-0.00039487606,0.05345523,-0.07804748,0.0658332,0.08180339,0.03238654,0.041596103,-0.0045786155,-0.031527046,0.033767365,-0.043127857,-0.048155993,-0.008139298,0.01852303,-0.03215714,-0.0028974677,-0.00064599526,-0.028920606,0.03055119,0.07603467,-0.057936672,0.012764122,-0.023463303,-0.0061960933,0.023166807,-0.021063747,0.030832294,-0.07573464,0.01774328,-0.041625842,-0.05201452,-0.036317553,-0.023584273,0.06454755,0.037271697,0.0029591285,0.03528548]	\N
31	security_officer	16	2025-12-10 02:52:41.789412	[0.07278095,-0.042876337,-0.06976455,-0.0027832694,0.010364588,0.011879254,-0.067362815,0.039892837,0.010903316,0.015820138,-0.055164352,0.03587826,-0.03712977,-0.056064747,-0.013716955,0.021343723,0.07955513,0.073745996,-0.005304301,-0.008434801,-0.052387573,0.045600973,0.035462312,-0.085396856,-0.041662607,-0.014429527,0.017859437,0.007983735,-0.037983064,-0.021416474,-0.07515656,0.036091562,0.018680299,0.015736552,-0.0058482583,-0.028835101,0.017638339,-0.0035135944,-0.0815644,-0.019840673,-0.004388652,0.010463677,-0.043722562,-0.034196097,-0.020283371,-0.020916574,0.02715221,-0.02592286,-0.070091665,0.010095859,-0.011807688,0.012556987,0.01307707,-0.012447852,-0.07567457,0.050551094,-0.040897757,0.07481108,0.0557397,-0.045031548,-0.016957128,0.047797736,-0.06954134,0.013730764,-0.021002365,0.045119345,0.06274154,0.00062049774,0.047735892,-0.014211729,-0.043170888,-0.03755845,0.009520507,0.018861067,0.024625106,-0.052896813,-0.06285795,-0.0077554807,0.0120704165,-0.039166942,0.0161512,0.01113277,0.033574495,-0.05459657,-0.031266112,0.040713903,-0.026257053,0.03724608,-0.101743825,0.012942281,-0.03406388,-0.03503247,0.08979935,-0.04606715,-0.06602198,0.043016843,0.046514455,0.020558815,-0.0516584,-0.018354556,-0.011053267,0.010818205,-0.0303314,0.004865375,0.011446434,-0.029467734,0.05736243,-0.102333345,-0.035183292,-0.024249965,-0.015941985,-0.07205613,-0.060645603,-0.023316948,0.0041532503,0.01593864,0.106330246,0.008290295,0.044285644,0.07214577,-0.05213261,-0.033899486,-0.048439015,0.025633799,-0.0076955543,-0.02623843,0.09998494,-0.025991,-0.087756604,-0.06270821,-0.064053416,-0.034887113,0.0077893226,-0.09989211,-0.05412903,-0.024063377,-0.026470065,-0.04474206,0.08214108,0.0073768785,0.01891898,0.029843519,-0.035757463,0.07813101,0.037086513,-0.0639195,-0.035467234,-0.046923827,0.02433155,0.084494576,0.004262363,-0.029894546,-0.019934403,0.023230715,0.072203286,-0.035277523,0.007377746,-0.0018518585,0.012554611,-0.010582338,0.047881413,0.015675552,-0.018990023,0.030591229,0.003660458,0.03709107,-0.030893987,-0.03717708,0.017322434,0.053708322,-0.035639852,0.054783974,-0.03592361,0.010538703,-0.005873723,0.01691022,0.0032243284,0.06738913,-0.04764936,0.0148482965,0.023493197,-0.018231248,-0.020518698,0.085168496,0.101157896,0.034194194,-0.02867221,0.053487368,0.10130096,0.081183985,0.051342003,0.023943985,-0.01706151,0.015648806,0.056286134,0.06207301,0.022033907,0.065321945,-0.0012647574,0.0023746255,0.06596113,-0.01325142,-0.0055980943,-0.02702068,-0.0011701882,0.0016051054,-0.010810034,0.054123882,0.007602661,0.085172154,0.015368521,0.0036930821,0.008675842,0.015159937,-0.047286782,0.03262576,-0.031137899,-0.0048540276,-0.104631886,0.09584467,-0.00017366017,0.039208855,-0.019262593,0.011872057,-0.007560171,0.01871203,-0.051446043,-0.04339387,0.013809708,0.048403963,0.03215508,-0.042940326,0.034534834,-0.1313355,-0.020823695,0.034642275,0.053116284,-0.051028702,0.03481597,-0.017513068,0.06824027,0.004090311,-0.00679643,-0.02284318,-0.05313511,0.055098902,0.01254571,-0.008392111,0.022577725,0.011326326,-0.033980895,0.023686312,0.055104714,-0.01748152,-0.0043161213,-0.012934705,0.02015376,-0.007367126,-0.01672403,0.021101,0.0133255655,0.053149987,-0.020248765,-0.00830756,-0.024466332,-0.015934648,0.0039082067,-0.021693619,-0.025956864,-0.056123998,-0.02944757,0.06469076,0.021683542,-0.08633709,-0.008928299,0.014973044,-0.045411564,-0.09348054,0.045258887,0.02153579,0.021971714,0.03277276,-0.061589725,-0.031568516,0.0009020415,0.0064283935,0.009496035,0.05597802,-0.0060217427,-0.01452948,-0.079460815,-0.012673933,0.05896916,0.013899261,0.0008185278,-0.06899644,0.016860677,0.06942712,0.08139223,-0.011772999,0.03523046,-0.017147219,-0.0075955796,0.07000683,-0.01846743,-0.014812335,0.04132073,-0.09340834,-0.030381152,0.0008020456,0.0075694816,0.073924825,-0.048939433,-0.07404797,0.039468616,0.0077967574,-0.026583703,0.07295189,0.061509904,-0.058779832,0.116120465,-0.08036705,0.0061222496,0.045155853,-0.05145351,-0.03095613,-0.026119811,-0.040130675,0.002867332,0.019212972,-0.018412882,0.03910137,0.032883693,-0.021406595,-0.017835801,0.13336393,-0.0021628374,-0.09620163,0.028281236,-0.038064156,0.019815337,0.054223873,-0.04707504,-0.023080377,-0.04182549,-0.0033025115,-0.0044971434,0.059029594,0.019453121,0.03751403,-0.012741691,0.01950238,-0.009046098,0.014886286,-0.043075476,-0.019481704,0.067225955,0.0049895807,-0.045007516,0.061241567,-0.04188092,-0.0007184417,-0.023432977,-0.0047918377,-0.02503289,0.03954995,0.06158089,-0.009292447,0.053127654,-0.003447531,-0.087582365,0.037546143,-0.055168457,0.027233727,-0.020392017,0.025534377,-0.06556873,0.037577573,-0.06664339,-0.0167799,-0.055704042,0.021724105,0.025982898,0.022962997,0.09189683,-0.020594425,0.029379038,-0.008390344,0.03435949,-0.030256094,-0.060915783,0.05431133,-0.007885401,-0.015930183,-0.053482834,0.04619285,0.060459904,0.012013914,0.030451072,-0.03160087,0.009330729,0.0005049414,-0.04903685,0.019359853,0.03156827,-0.07954424,-0.07470471,-0.054068815,-0.0007177908,-0.012771809,0.039237812,-0.065761335,0.043626778,0.04258558,-0.033947177,0.05488063,0.09245575,0.02317538,-0.041754067,-0.034247525,0.030173708,0.064193666,0.06560716,0.098131225,-0.011060797,-0.048117008,-0.0015809371,-0.0113307005,-0.07445097,-0.064016506,-0.08158655,-0.04336111,-0.03738352,-0.108968064,-0.005942127,0.03277832,0.040515214,-0.00020228853,0.022519665,-0.041676138,-0.03488323,0.025309885,0.027811443,0.05927897,0.009663518,-0.031865492,0.04202195,0.002403063,-0.069656946,-0.022608934,0.022541378,0.08812662,0.037585583,-0.01758784,-0.008896646,-0.06532088,0.0264712,0.046683725,0.049712393,0.040845096,0.04260943,0.07405048,0.036688402,-0.031098844,0.03165794,0.04765107,-0.023694834,-0.028708937,0.10948102,-0.01280756,0.05019044,-0.0010735998,0.018374184,0.03450517,-0.022492215,-0.028899843,0.030395325,-0.05550158,0.05860459,0.02765313,0.010304398,0.0020809919,0.032350115,-0.025876865,0.09984668,-0.014817522,-0.024450652,-0.04281716,0.033705804,-0.01821261,0.03690191,-0.04099186,-0.008916878,0.0051807603,0.04801181,-0.059814677,0.08055222,-0.0088994745,-0.010709711,-0.0033263299,-0.036076896,0.053949255,-0.074195944,0.05255677,-0.013659655,-9.8343684e-05,-0.037537392,-0.027276425,-0.014522463,-0.0068555577,-0.05420269,0.013862284]	\N
32	security_officer	17	2025-12-10 02:52:45.685136	[0.07540114,-0.059698615,-0.066151984,0.04986454,0.038632296,0.047043685,-0.030009829,0.024590094,-0.012198881,0.0031385522,-0.03341384,-0.0033881946,-0.00015229567,-0.057239853,-0.015836554,0.0062949285,0.064854115,0.10918687,0.022449879,-0.026759125,-0.035107564,0.042019226,0.04991551,-0.023512967,-0.042276468,0.020855216,0.03065012,0.0011674907,-0.032571435,-0.022683632,-0.021506933,0.048104472,-0.02012993,-0.006975561,0.002303173,-0.059967123,0.054759234,-0.021508157,-0.098679416,-0.060690932,-0.018712694,0.012206772,-0.008512149,-0.049867213,0.015475784,-0.0059853774,0.01684569,-0.024299886,-0.06505956,-0.008918842,0.0038037614,0.010049913,0.00034600234,-0.013319947,-0.047601808,0.01577764,-0.032881457,0.04804853,0.09439392,0.01540127,-0.015945887,0.023993833,-0.033802222,0.0031776454,-0.04598501,0.031227434,0.03316935,-0.004573585,0.05524351,0.004855379,-0.06681276,-0.051631805,0.041268475,0.05607728,0.07137252,-0.046665628,-0.02411197,-0.021194292,0.0067483597,-0.054968413,0.045076907,0.042360034,0.041779492,-0.03437418,-0.056795478,0.057088938,0.009820857,0.03327642,-0.048093252,-0.03433888,-0.07511776,-0.0014112296,0.09914938,0.05001446,-0.05794527,0.03663546,0.005453105,-0.010201688,-0.038122784,0.017778145,-0.01564818,-0.0018713077,-0.025671136,-0.026031757,-0.0067949085,-0.057522617,-0.011322056,-0.15349688,-0.02730856,-0.04057835,0.0037503787,-0.00438352,-0.10969324,-0.028884642,0.041119043,0.029695183,0.09256183,-0.02508253,-0.0055274796,0.10357262,-0.013213441,0.011162324,-0.031148985,-0.010526472,-0.0072549675,-0.04058404,0.06427085,-0.0020279298,0.0051241657,-0.014309919,-0.0053048306,-0.057923175,0.01878198,-0.024260702,-0.065338776,0.014709618,-0.049148403,-0.07333876,0.08428067,-0.0015765063,0.016969051,0.061903693,0.0008386836,0.080562934,0.057705704,-0.06587201,-0.02608468,-0.027768722,0.09152398,0.07641886,-0.0071498216,-0.019354189,0.0276814,0.04640512,0.04624374,-0.09858757,-0.044885453,-0.021179901,0.0054199346,-0.07928909,0.0071669435,0.022740547,-0.034483477,0.046883203,0.045755234,0.03795961,-0.07532657,-0.009040176,0.0015317629,0.051160604,0.020358225,0.042668913,-0.034950174,0.049203645,-0.02011657,0.023668265,9.904549e-05,0.12121643,-0.03920045,0.056049675,0.010453031,0.0051678065,0.021709783,0.015620605,0.079398625,0.0021280677,-0.00043450398,0.004162639,0.10504469,0.04490316,0.053460646,0.05535391,0.027045483,-0.017701123,0.052447323,0.041955553,0.02388435,0.054797217,0.036512107,-0.007286549,0.09197903,-0.005855748,0.039852675,-0.002651426,0.01720536,0.02101347,0.01180625,0.060037583,0.015055894,0.052940886,0.032033715,-0.007475136,-0.0014027281,0.087526515,-0.025342915,0.07044871,-0.0029990233,-0.025092853,-0.106960446,0.06269039,0.0158791,0.019465787,0.0025486338,0.020632446,-0.009040273,0.006746692,-0.061673153,-0.0036687483,0.048240334,0.019617014,0.048689444,-0.0023565725,0.013157371,-0.08678656,-0.029557861,0.043946203,-0.005625567,-0.010044988,0.048653714,-0.049064495,0.03882911,0.020313678,0.017729621,0.023470908,-0.023175526,0.05693302,0.019783817,-0.011665989,0.011931592,0.074490584,-0.041007265,0.0032048232,0.059985746,-0.015139579,-0.011758773,-0.08159192,-0.03723929,-0.020327963,0.001697286,-0.052790698,-0.022708286,0.029450879,0.0022985288,-0.026883159,-0.04335663,-0.06816144,0.024544034,-0.02150556,-0.020669453,-0.08351845,0.021302925,0.06364874,0.0385993,-0.056314208,-0.0073192464,-0.01763219,-0.0464641,-0.046925295,0.0500033,0.070418864,0.010366092,0.018336248,-0.10113361,-0.07022907,0.012046143,0.012190527,0.002873099,0.010222838,-0.02500382,-0.008762735,-0.053308353,0.011049046,0.008152888,0.050719686,0.038644217,-0.015855934,0.0016429937,0.03388417,0.06549232,-0.027146103,0.09191912,0.009015453,0.039152488,0.08610498,-0.010679065,0.008517411,-0.0032274087,-0.050226342,-0.025743077,0.010884787,0.008557103,0.07816753,-0.008990503,-0.04535874,0.046063084,0.042629305,0.026059907,0.0347395,0.097947486,-0.07047027,0.12118759,-0.09195871,0.024960522,0.030888733,-0.04840317,-0.01996312,-0.009741094,-0.04962247,-0.011021333,-0.028169604,-0.019251803,0.024676025,0.049778637,-0.022309087,-0.015589768,0.091313235,0.023548508,-0.058955107,0.009652956,-0.05242248,0.0512702,0.03238806,-0.054106154,-0.03794217,-0.015137486,-0.01807103,-0.023405211,0.08461432,0.03546942,0.032199677,0.02238644,-0.026424859,-0.030718416,0.045794044,-0.04165885,0.042735383,0.06961018,-0.011226422,-0.061168645,0.0691852,-0.017058564,0.01570178,0.003009307,0.011476851,-0.022022638,0.03277101,0.028210126,-0.02008816,0.02312784,0.0071807876,-0.035984,0.066562295,-0.07835715,0.0205666,-0.0523797,0.053079378,-0.05525697,0.025377491,-0.010958992,-0.016788727,-0.07616639,0.04569736,0.042548385,0.055642013,0.0880535,-0.009607226,-0.0072109886,-0.04694738,0.0021894223,-0.05275212,-0.050655343,0.04986944,0.028787563,-0.029668873,-0.024279848,0.07017082,0.06967468,0.06474156,0.019981476,-0.05703634,-0.0071643908,-0.029359313,-0.033754602,0.07522641,0.04423536,-0.09820246,-0.06531805,-0.015054058,0.026963793,0.041654717,0.1031362,-0.05311471,0.05326095,0.027361939,-0.029672751,0.046966173,0.05921655,0.00714225,-0.034673464,0.030564304,0.0079452,-0.005455501,0.029562613,0.046512235,-0.058797583,-0.0005831158,0.004645363,0.022519313,-0.06466101,-0.05584699,-0.06508347,-0.0020584622,-0.054397374,-0.07556885,0.0071317893,0.06292093,0.025799002,-0.009333285,0.053370308,-0.018969946,-0.06332323,0.0101234205,0.0008340809,0.05324592,0.057338703,-0.0521319,-0.02211407,0.04342691,-0.012769835,-0.03018158,0.020055884,0.060145024,0.007140223,-0.026502125,-0.007874998,-0.014013338,-0.06412832,0.014622017,0.047341175,0.083688915,0.019907847,0.0957491,0.047157757,0.009912196,-0.020656548,-0.015145533,-0.0128697315,-0.03377254,0.06773813,0.0014785256,0.04984395,-0.0023117561,-0.013761016,0.027102444,-0.023401367,0.0028682281,0.016539186,-0.050399765,0.045530688,0.02434001,-0.02543345,-0.015014223,0.03382552,-0.0054758685,0.05432703,-0.04044691,-0.09626221,0.0031369606,0.018061072,-0.032832053,0.028729541,-0.0662252,-0.0028189986,0.020716287,0.08351077,-0.0624551,0.081576385,0.019719081,0.0027075848,0.016182346,0.030486878,0.022910245,-0.056003097,-0.00157298,-0.025193527,0.0002897042,-0.030242343,-0.014562197,0.008342355,0.017943837,-0.044679597,-0.010827033]	\N
\.


--
-- TOC entry 5226 (class 0 OID 42771)
-- Dependencies: 231
-- Data for Name: internal_staff; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.internal_staff (staff_id, full_name, department, contact_number, staff_type, user_id, registered_at) FROM stdin;
\.


--
-- TOC entry 5216 (class 0 OID 42669)
-- Dependencies: 221
-- Data for Name: residents; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.residents (resident_id, full_name, unit_number, contact_number, user_id, registered_at) FROM stdin;
1	John Tan	B-12-05	91234567	2	2025-11-12 11:06:13.172525
2	Alice Lim	B-12-06	91234568	4	2025-11-12 11:06:13.172525
3	Bob Ong	B-12-07	91234569	5	2025-11-12 11:06:13.172525
20	Joshua Woon	B-29-302	98162700	\N	2025-12-04 02:54:10.30757
\.


--
-- TOC entry 5212 (class 0 OID 42641)
-- Dependencies: 217
-- Data for Name: roles; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.roles (role_id, role_name) FROM stdin;
1	Admin
2	Resident
3	Visitor
4	Security
5	resident
6	visitor
7	security_officer
8	internal_staff
9	temp_staff
10	admin
11	ADMIN
\.


--
-- TOC entry 5224 (class 0 OID 42746)
-- Dependencies: 229
-- Data for Name: security_officers; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.security_officers (officer_id, full_name, contact_number, shift, active, registered_at) FROM stdin;
12	New Officer	\N	\N	t	2025-12-04 07:43:09.407716
13	New Officer	\N	\N	t	2025-12-08 01:46:54.663475
14	New Officer	\N	\N	t	2025-12-08 01:47:08.720504
1	Joshua Elijah	98152700	PM	t	2025-12-08 09:36:01.989347
15	New Officer	\N	\N	t	2025-12-10 00:31:27.229144
16	New Officer	\N	\N	t	2025-12-10 02:52:41.776932
17	New Officer	\N	\N	t	2025-12-10 02:52:45.671489
\.


--
-- TOC entry 5230 (class 0 OID 42806)
-- Dependencies: 235
-- Data for Name: staff; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.staff (staff_id, user_id, full_name, contact_number, "position", face_encoding, is_active, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 5234 (class 0 OID 42842)
-- Dependencies: 239
-- Data for Name: staff_attendance; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.staff_attendance (attendance_id, staff_id, entry_time, exit_time, duration_hours, verification_method, entry_confidence, exit_confidence, location, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 5232 (class 0 OID 42826)
-- Dependencies: 237
-- Data for Name: staff_schedules; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.staff_schedules (schedule_id, staff_id, shift_date, shift_start, shift_end, task_description, created_at) FROM stdin;
\.


--
-- TOC entry 5228 (class 0 OID 42784)
-- Dependencies: 233
-- Data for Name: temp_staff; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.temp_staff (temp_id, full_name, company, contact_number, contract_start, contract_end, allowed_rate_min, allowed_rate_max, user_id, registered_at) FROM stdin;
\.


--
-- TOC entry 5214 (class 0 OID 42650)
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
8	admin1	admin@example.com	...	10	2025-12-05 11:59:09.440753
9	admin_test	admin_test@example.com	scrypt:32768:8:1$NZyoAIz4fqljiRei$4f63f3ae86424d7dd9f7d0fd29096ce2d58966e6bf9247b5b512adfbd8b5d045746a1e7175e53f71f7be9d261647efcae4896f9c8a7ac0cfbea26e4f924991bb	11	2025-12-05 12:43:29.01668
14	admin_test_601	admin695@example.com	scrypt:32768:8:1$hBvy2Hma1rCUe9ND$aacd8aa2d34432969cf215b75a20f437af0c97f264178bb38b439516092c86eff95523328414a2e34286b37639040b722cdb1bd95e6b48822262d53f97c8fd10	11	2025-12-05 12:51:59.985357
15	admin_test_33	admin297@example.com	scrypt:32768:8:1$U5DjqaK1VPIFci7y$f87fdb9d2c79565ca6362a741e2e8c1e03fc51ed3b6da5c6bbcb351a3a128ed05abbe35ec65b5f60b010ccf59c9c0d601770ea4db1b14cb7e924bea0af616e5b	11	2025-12-05 12:52:02.120944
16	admin_test_785	admin546@example.com	scrypt:32768:8:1$K5P43hLnIifVQuI5$a0d3ca10f7fe11abd6aea62eb035907f1447689ec66eda18e75b9ec5295087bd4cd846ce31875ce62ab6a9f6430e368d5a10f21203dfee301facef03f48b90f7	11	2025-12-05 12:52:03.736236
17	admin_test_392	admin269@example.com	scrypt:32768:8:1$iC1G9v5u5AgU4c6q$b30f33473711cbbda115cbe11a9a55c29b23397e6fbc992682d0b30c3532e5babdd3f172a2384ebd27d3ac8778641cf5925cf3bce2696aaed87ab91269daf438	11	2025-12-05 12:54:39.844496
18	admin_test_464	admin766@example.com	scrypt:32768:8:1$SkBdgqIRw3ea2bd5$7e7c739d1f91622977a9bad523af51d74988c8ed8692b01beeff9b5ff46ceb04de712314caab305028d308ade1a4cacb2b5b672bc2cda1c64abe6eb13532e87e	11	2025-12-05 12:59:50.527209
\.


--
-- TOC entry 5218 (class 0 OID 42684)
-- Dependencies: 223
-- Data for Name: visitors; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.visitors (visitor_id, full_name, contact_number, visiting_unit, check_in, check_out, approved_by) FROM stdin;
5	Abi W	96804721	B-29-302	2025-12-04 03:48:11.400952	\N	\N
\.


--
-- TOC entry 5253 (class 0 OID 0)
-- Dependencies: 226
-- Name: access_logs_log_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.access_logs_log_id_seq', 51, true);


--
-- TOC entry 5254 (class 0 OID 0)
-- Dependencies: 224
-- Name: face_embeddings_embedding_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.face_embeddings_embedding_id_seq', 32, true);


--
-- TOC entry 5255 (class 0 OID 0)
-- Dependencies: 230
-- Name: internal_staff_staff_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.internal_staff_staff_id_seq', 1, false);


--
-- TOC entry 5256 (class 0 OID 0)
-- Dependencies: 220
-- Name: residents_resident_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.residents_resident_id_seq', 20, true);


--
-- TOC entry 5257 (class 0 OID 0)
-- Dependencies: 216
-- Name: roles_role_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.roles_role_id_seq', 11, true);


--
-- TOC entry 5258 (class 0 OID 0)
-- Dependencies: 228
-- Name: security_officers_officer_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.security_officers_officer_id_seq', 17, true);


--
-- TOC entry 5259 (class 0 OID 0)
-- Dependencies: 238
-- Name: staff_attendance_attendance_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.staff_attendance_attendance_id_seq', 1, false);


--
-- TOC entry 5260 (class 0 OID 0)
-- Dependencies: 236
-- Name: staff_schedules_schedule_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.staff_schedules_schedule_id_seq', 1, false);


--
-- TOC entry 5261 (class 0 OID 0)
-- Dependencies: 234
-- Name: staff_staff_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.staff_staff_id_seq', 1, false);


--
-- TOC entry 5262 (class 0 OID 0)
-- Dependencies: 232
-- Name: temp_staff_temp_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.temp_staff_temp_id_seq', 1, false);


--
-- TOC entry 5263 (class 0 OID 0)
-- Dependencies: 218
-- Name: users_user_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.users_user_id_seq', 18, true);


--
-- TOC entry 5264 (class 0 OID 0)
-- Dependencies: 222
-- Name: visitors_visitor_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.visitors_visitor_id_seq', 5, true);


--
-- TOC entry 5040 (class 2606 OID 42721)
-- Name: access_logs access_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.access_logs
    ADD CONSTRAINT access_logs_pkey PRIMARY KEY (log_id);


--
-- TOC entry 5038 (class 2606 OID 42705)
-- Name: face_embeddings face_embeddings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.face_embeddings
    ADD CONSTRAINT face_embeddings_pkey PRIMARY KEY (embedding_id);


--
-- TOC entry 5044 (class 2606 OID 42777)
-- Name: internal_staff internal_staff_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.internal_staff
    ADD CONSTRAINT internal_staff_pkey PRIMARY KEY (staff_id);


--
-- TOC entry 5032 (class 2606 OID 42675)
-- Name: residents residents_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.residents
    ADD CONSTRAINT residents_pkey PRIMARY KEY (resident_id);


--
-- TOC entry 5034 (class 2606 OID 42677)
-- Name: residents residents_user_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.residents
    ADD CONSTRAINT residents_user_id_key UNIQUE (user_id);


--
-- TOC entry 5022 (class 2606 OID 42646)
-- Name: roles roles_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_pkey PRIMARY KEY (role_id);


--
-- TOC entry 5024 (class 2606 OID 42648)
-- Name: roles roles_role_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_role_name_key UNIQUE (role_name);


--
-- TOC entry 5042 (class 2606 OID 42753)
-- Name: security_officers security_officers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.security_officers
    ADD CONSTRAINT security_officers_pkey PRIMARY KEY (officer_id);


--
-- TOC entry 5057 (class 2606 OID 42850)
-- Name: staff_attendance staff_attendance_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.staff_attendance
    ADD CONSTRAINT staff_attendance_pkey PRIMARY KEY (attendance_id);


--
-- TOC entry 5049 (class 2606 OID 42816)
-- Name: staff staff_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.staff
    ADD CONSTRAINT staff_pkey PRIMARY KEY (staff_id);


--
-- TOC entry 5054 (class 2606 OID 42834)
-- Name: staff_schedules staff_schedules_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.staff_schedules
    ADD CONSTRAINT staff_schedules_pkey PRIMARY KEY (schedule_id);


--
-- TOC entry 5051 (class 2606 OID 42818)
-- Name: staff staff_user_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.staff
    ADD CONSTRAINT staff_user_id_key UNIQUE (user_id);


--
-- TOC entry 5046 (class 2606 OID 42790)
-- Name: temp_staff temp_staff_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.temp_staff
    ADD CONSTRAINT temp_staff_pkey PRIMARY KEY (temp_id);


--
-- TOC entry 5026 (class 2606 OID 42662)
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- TOC entry 5028 (class 2606 OID 42658)
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (user_id);


--
-- TOC entry 5030 (class 2606 OID 42660)
-- Name: users users_username_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_username_key UNIQUE (username);


--
-- TOC entry 5036 (class 2606 OID 42689)
-- Name: visitors visitors_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.visitors
    ADD CONSTRAINT visitors_pkey PRIMARY KEY (visitor_id);


--
-- TOC entry 5055 (class 1259 OID 42856)
-- Name: idx_staff_attendance_time; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_staff_attendance_time ON public.staff_attendance USING btree (staff_id, entry_time);


--
-- TOC entry 5047 (class 1259 OID 42824)
-- Name: idx_staff_face_encoding; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_staff_face_encoding ON public.staff USING ivfflat (face_encoding public.vector_cosine_ops) WITH (lists='100');


--
-- TOC entry 5052 (class 1259 OID 42840)
-- Name: idx_staff_schedules_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_staff_schedules_date ON public.staff_schedules USING btree (staff_id, shift_date);


--
-- TOC entry 5067 (class 2620 OID 42858)
-- Name: staff_attendance trg_calculate_duration; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_calculate_duration BEFORE INSERT OR UPDATE ON public.staff_attendance FOR EACH ROW EXECUTE FUNCTION public.calculate_attendance_duration();


--
-- TOC entry 5061 (class 2606 OID 42722)
-- Name: access_logs access_logs_embedding_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.access_logs
    ADD CONSTRAINT access_logs_embedding_id_fkey FOREIGN KEY (embedding_id) REFERENCES public.face_embeddings(embedding_id) ON DELETE SET NULL;


--
-- TOC entry 5062 (class 2606 OID 42778)
-- Name: internal_staff internal_staff_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.internal_staff
    ADD CONSTRAINT internal_staff_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- TOC entry 5059 (class 2606 OID 42678)
-- Name: residents residents_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.residents
    ADD CONSTRAINT residents_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- TOC entry 5066 (class 2606 OID 42851)
-- Name: staff_attendance staff_attendance_staff_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.staff_attendance
    ADD CONSTRAINT staff_attendance_staff_id_fkey FOREIGN KEY (staff_id) REFERENCES public.staff(staff_id) ON DELETE CASCADE;


--
-- TOC entry 5065 (class 2606 OID 42835)
-- Name: staff_schedules staff_schedules_staff_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.staff_schedules
    ADD CONSTRAINT staff_schedules_staff_id_fkey FOREIGN KEY (staff_id) REFERENCES public.staff(staff_id) ON DELETE CASCADE;


--
-- TOC entry 5064 (class 2606 OID 42819)
-- Name: staff staff_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.staff
    ADD CONSTRAINT staff_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- TOC entry 5063 (class 2606 OID 42791)
-- Name: temp_staff temp_staff_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.temp_staff
    ADD CONSTRAINT temp_staff_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- TOC entry 5058 (class 2606 OID 42663)
-- Name: users users_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(role_id) ON DELETE CASCADE;


--
-- TOC entry 5060 (class 2606 OID 42690)
-- Name: visitors visitors_approved_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.visitors
    ADD CONSTRAINT visitors_approved_by_fkey FOREIGN KEY (approved_by) REFERENCES public.residents(resident_id) ON DELETE SET NULL;


-- Completed on 2025-12-10 12:37:56

--
-- PostgreSQL database dump complete
--

--Add new columns to users table
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'active';
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS access_level VARCHAR(50) DEFAULT 'standard';

--Update existing users to have 'active' status
UPDATE public.users SET status = 'active' WHERE status IS NULL;
UPDATE public.users SET access_level = 'standard' WHERE access_level IS NULL;

-- Add new roles (Guest and TEMP_WORKER)
INSERT INTO public.roles (role_id, role_name) VALUES (5, 'Guest') ON CONFLICT (role_id) DO NOTHING;
INSERT INTO public.roles (role_id, role_name) VALUES (6, 'TEMP_WORKER') ON CONFLICT (role_id) DO NOTHING;

--Create temp_workers table
CREATE TABLE IF NOT EXISTS public.temp_workers (
    temp_worker_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES public.users(user_id) ON DELETE CASCADE,
    resident_id INTEGER REFERENCES public.residents(resident_id) ON DELETE CASCADE,
    work_start_date DATE,
    work_end_date DATE,
    work_schedule VARCHAR(255),
    work_details TEXT,
    id_document_path VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_status ON public.users(status);
CREATE INDEX IF NOT EXISTS idx_users_access_level ON public.users(access_level);
CREATE INDEX IF NOT EXISTS idx_temp_workers_user_id ON public.temp_workers(user_id);
CREATE INDEX IF NOT EXISTS idx_temp_workers_dates ON public.temp_workers(work_start_date, work_end_date);

--  Verify changes
SELECT 'Users table columns:' as info;
SELECT column_name, data_type, column_default 
FROM information_schema.columns 
WHERE table_name = 'users' AND table_schema = 'public'
ORDER BY ordinal_position;

SELECT 'All roles:' as info;
SELECT * FROM public.roles ORDER BY role_id;

SELECT 'Temp workers table exists:' as info;
SELECT EXISTS (
    SELECT FROM information_schema.tables 
    WHERE table_name = 'temp_workers' AND table_schema = 'public'
) as temp_workers_exists;

-- Fix access_logs person_type to include all user categories
-- This script adds support for temp_staff and ADMIN user types

-- Drop the existing constraint
ALTER TABLE public.access_logs
DROP CONSTRAINT IF EXISTS access_logs_person_type_check;

-- Add updated constraint with all user types
ALTER TABLE public.access_logs
ADD CONSTRAINT access_logs_person_type_check
CHECK (
    person_type IN (
        'resident',
        'visitor',
        'security_officer',
        'internal_staff',
        'temp_staff',
        'ADMIN',
        'unknown'
    )
);

-- Update any existing records that might have null or invalid person_type
UPDATE public.access_logs
SET person_type = 'unknown'
WHERE person_type IS NULL OR person_type NOT IN (
    'resident',
    'visitor',
    'security_officer',
    'internal_staff',
    'temp_staff',
    'ADMIN',
    'unknown'
);

-- Verify the change
SELECT
    constraint_name,
    check_clause
FROM information_schema.check_constraints
WHERE constraint_name = 'access_logs_person_type_check';

-- Show current person_type distribution
SELECT
    person_type,
    COUNT(*) as count,
    COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () as percentage
FROM public.access_logs
GROUP BY person_type
ORDER BY count DESC;
