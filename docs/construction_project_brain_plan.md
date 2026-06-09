# Construction Project Brain: Research and Implementation Plan

## Goal

Design and build a functioning project intelligence system for construction-sector projects. The system should ingest files and communications scattered across folder structures and channels, extract reliable project knowledge, show a knowledge graph of the whole project, maintain a timeline of deliverables, and propose task/timeline updates when new emails, meeting minutes, notes, contracts, drawings, and other documentation arrive. Applying updates should require human approval unless the update is explicitly classified as low-risk metadata and the user has enabled that mode.

The recommended approach is not to blindly upload all documents into a model. Instead, the system should combine deterministic document processing, structured data storage, retrieval-augmented generation (RAG), a knowledge graph, and human-approved AI extraction.

## Alignment With the Current Agent Setup

This plan is aligned with the strengthened `AGENTS.md` rules for this repository:

- Treat real construction project files as confidential by default.
- Start with one-project, read-only ingestion before automation that mutates state.
- Preserve citations, source references, hashes, timestamps, confidence, extraction method, and review status for every extracted project fact.
- Do not let models directly rewrite canonical project state.
- Represent timeline, task, contract, payment, liability, scope, and safety-impacting changes as proposed updates requiring human approval.
- Use local-first parsing and least-data model calls: parse locally, retrieve relevant snippets, pass only necessary context to a model, and store outputs as cited proposals.
- Do not commit real documents, emails, contracts, drawings, local databases, secrets, or personal data to this repository.
- Use synthetic or sanitized sample data for fixtures, demos, and tests.

The main adjustment from the original product idea is that the product should not be framed as a fully autonomous updater at the beginning. The safer target is an evidence-backed project control assistant: it detects likely changes, explains why, shows the source evidence, predicts impact, and waits for approval before changing timelines, tasks, obligations, or reports.

---

## 1. Key Questions to Resolve

### A. Scope and Data Sources

1. Where are the files stored?
   - Local folders
   - SharePoint / OneDrive
   - Google Drive
   - Dropbox
   - Procore / Dalux / Autodesk Construction Cloud / BIM 360
   - Email inboxes
   - Teams / Slack
2. Approximate data volume:
   - Number of files
   - Total GB/TB
   - Number of active projects
3. File types:
   - PDF
   - scanned PDF
   - DOCX
   - XLSX
   - emails / `.eml` / `.msg`
   - drawings / DWG / IFC / RVT / drawing PDFs
   - photos
   - contracts
   - schedules: MS Project, Primavera P6, Excel, PDF
4. Languages:
   - English
   - Danish
   - mixed

### B. Project-Management Outcomes

5. What should the brain maintain?
   - Deliverables timeline
   - Contract obligations
   - RFI log
   - Change orders
   - Meeting action items
   - Risks/issues
   - Stakeholder map
   - Document register
   - Design decisions
   - Procurement deadlines
6. What should the system propose updates for?
   - Tasks
   - Milestones
   - Deadlines
   - Dependencies
   - Responsibility assignments
   - Risk status
   - Low-risk metadata that may later be auto-updated after approval of the mode
7. Existing task/project system integrations:
   - MS Planner
   - Jira
   - Linear
   - Monday
   - Asana
   - Procore tasks
   - custom dashboard

### C. Security and Legal Constraints

8. Can project data be sent to cloud LLMs?
   - Yes
   - No
   - Only redacted snippets
   - Only certain projects
   - Must use on-prem/local models
9. Are contracts, tender material, or confidential documents included?
10. Is an audit trail required for every graph/timeline/task update?

### D. User Experience

11. Who are the users?
   - Project manager
   - Construction manager
   - Design team
   - Legal/contracts team
   - Client
   - Subcontractors
12. Desired interface:
   - Dashboard
   - Chat interface
   - Graph viewer
   - Timeline/Gantt
   - Automated email summaries
   - Teams bot
13. Which update classes must always require approval, and which low-risk metadata fields could later be auto-updated after the system proves accuracy?

---

## 2. Recommended Architecture

Treat the product as a construction project intelligence layer, not merely a chatbot over documents.

```text
Sources
  ├─ folders / SharePoint / Drive
  ├─ emails
  ├─ meeting minutes
  ├─ contracts
  ├─ schedules
  ├─ drawings/specs
  └─ notes/photos

        ↓

Ingestion Layer
  ├─ file watcher / connectors
  ├─ version detection
  ├─ deduplication
  ├─ metadata extraction
  └─ permissions mapping

        ↓

Document Understanding Layer
  ├─ text extraction
  ├─ OCR for scanned documents
  ├─ table extraction
  ├─ email thread parsing
  ├─ drawing/spec metadata parsing
  └─ chunking with citations

        ↓

AI Extraction Layer
  ├─ entities
  ├─ dates
  ├─ obligations
  ├─ deliverables
  ├─ tasks/action items
  ├─ risks/issues
  ├─ dependencies
  ├─ stakeholders
  └─ changes vs previous versions

        ↓

Project Brain
  ├─ Knowledge graph
  ├─ Vector search / RAG index
  ├─ Timeline/task database
  ├─ Document register
  ├─ Audit trail
  └─ Change/event log

        ↓

User Interfaces
  ├─ graph view
  ├─ timeline/Gantt
  ├─ chat with citations
  ├─ alerts
  ├─ task board
  └─ reports
```

---

## 3. Core Data Model

The system should store structured project objects, not just text chunks.

### Project

- name
- phase
- client
- site
- contract type
- start/end dates

### Organization / Person

- client
- architect
- engineer
- general contractor
- subcontractor
- supplier
- authority
- contact person
- role
- responsibility

### Document

- title
- type
- source
- version/revision
- date
- author
- discipline
- linked project/package
- extracted text
- citations

### Deliverable

- name
- description
- due date
- responsible party
- dependencies
- status
- source evidence

### Milestone

- planned date
- revised date
- actual date
- reason for change
- linked documents/events

### Task / Action Item

- description
- owner
- due date
- status
- origin: meeting minute/email/contract/etc.
- confidence score
- approval requirement

### Contract Obligation

- responsible party
- obligation text
- due date or trigger condition
- penalty/liability if relevant
- source clause citation

### Risk / Issue

- description
- category
- severity
- probability
- owner
- mitigation
- source evidence

### Change Event

- what changed
- previous value
- new value
- source document/email
- model confidence
- approval status

### Example Relationships

- `Person WORKS_FOR Organization`
- `Organization RESPONSIBLE_FOR Deliverable`
- `Deliverable DEPENDS_ON Milestone`
- `ContractClause CREATES_OBLIGATION Obligation`
- `MeetingMinute CREATES_TASK Task`
- `Email UPDATES_DUE_DATE Deliverable`
- `Document SUPERSEDES Document`
- `Drawing REVISION_OF Drawing`
- `Risk AFFECTS Milestone`
- `ChangeOrder MODIFIES Contract`

---

## 4. Extraction Strategy

Use different extraction methods depending on the file type.

### Native Text Files

- DOCX: parse with `python-docx`.
- XLSX: parse sheets, tables, and named ranges with `openpyxl` or `pandas`.
- Text-based PDFs: use PyMuPDF, pdfplumber, or similar.
- Emails: parse headers, sender/recipients, thread IDs, attachments, and quoted text.

### Scanned PDFs and Images

OCR is required. Options include:

- Azure Document Intelligence
- Google Document AI
- AWS Textract
- Tesseract
- marker-pdf

Construction documents often include stamps, tables, signatures, and drawings. Plain OCR may be insufficient for important contractual or technical documents.

### Drawings and Specifications

For drawing PDFs, the first practical target should be metadata extraction:

- title block
- drawing number
- revision
- discipline
- issue date
- project name
- scale
- sheet title

Full semantic interpretation of construction drawings should be treated as a later phase. For the MVP, extract drawing metadata and link drawings to packages, deliverables, and revisions.

### Meeting Minutes

Extract:

- attendees
- decisions
- action items
- owners
- due dates
- open issues
- references to drawings/RFIs/contracts
- changes since previous meeting

### Contracts

Extract:

- parties
- scope
- milestones
- payment terms
- notice periods
- approval deadlines
- obligations
- termination clauses
- penalties/liquidated damages
- change procedure
- document hierarchy

Contracts require high caution. Extracted obligations should always include citations and should require human approval before becoming authoritative.

---

## 5. Should Files or Data Be Passed Directly to a Model?

### Option 1: Pass Whole Files Directly to an LLM

This option is only acceptable for synthetic, sanitized, public, or explicitly approved documents. It is not the default for confidential project files.

Good for:

- small batches
- one-off analysis
- early prototyping
- summarizing a single contract or meeting minute

Bad for:

- large project archives
- ongoing updates
- auditability
- cost control
- privacy
- version tracking
- repeatable extraction
- timeline consistency

Verdict: useful for prototypes with approved data, not enough for the full project brain, and not acceptable for confidential project archives unless explicitly authorized.

### Option 2: Parse Files, Chunk Them, and Use RAG

Good for:

- asking questions across many files
- source citations
- lower cost
- controlled context
- keeping original documents outside the model

Pipeline:

1. Extract text and metadata.
2. Split into meaningful chunks.
3. Store chunks with document/page/paragraph references.
4. Embed chunks into a vector database.
5. At query time, retrieve relevant chunks.
6. Pass only those snippets to the model.
7. Answer with citations.

Verdict: best foundation for document Q&A.

### Option 3: Use LLMs for Structured Extraction

This is essential for automatic project intelligence.

Instead of only asking the model to summarize, ask it to output structured JSON:

```json
{
  "deliverables": [],
  "tasks": [],
  "dates": [],
  "obligations": [],
  "risks": [],
  "stakeholders": [],
  "relationships": []
}
```

Then validate the JSON, attach citations, and create proposed graph/timeline updates through controlled application logic. The canonical project state is changed only after the relevant approval rule passes.

Verdict: best approach for producing evidence-backed update proposals for the knowledge graph and timelines.

### Option 4: Fine-Tune a Model on the Project Files

Usually not the right answer.

Fine-tuning is useful for:

- learning extraction style
- classification labels
- company-specific document patterns
- tone/style

Fine-tuning is bad for:

- storing changing project facts
- contract knowledge
- timeline state
- source-grounded answers

Verdict: do not fine-tune for project memory. Use RAG plus structured databases. Fine-tune only later if extraction quality needs improvement.

### Option 5: Local or On-Prem Models

Good if confidentiality is strict.

Possible setup:

- Local parsing and indexing.
- Local embeddings.
- Local LLM for classification/extraction where possible.
- Optional cloud LLM only for approved or redacted snippets.

Verdict: important if contracts, tenders, or private project data cannot leave the controlled environment.

---

## 6. Recommended Technical Stack

### Storage

- PostgreSQL: canonical project data, tasks, timelines, audit log
- Neo4j or Memgraph: knowledge graph
- Qdrant, Weaviate, or pgvector: vector search
- Object/file storage: original documents and extracted artifacts

### Extraction

- PyMuPDF/pdfplumber for text PDFs
- `python-docx` for Word
- `openpyxl`/`pandas` for Excel
- email parser for `.eml`/`.msg`
- OCR engine for scans:
  - Azure Document Intelligence if cloud is allowed
  - Tesseract/marker-pdf if local is preferred
  - AWS Textract/Google Document AI as alternatives

### AI Layer

Use LLMs for:

- classification
- structured extraction
- timeline update proposals
- relationship extraction
- summarization
- query answering

Requirements:

- schema-constrained JSON outputs
- citations for every extracted fact
- confidence scoring
- validation before database writes

### Backend

- Python FastAPI
- background workers with Celery, RQ, or Arq
- scheduled ingestion jobs
- event-driven processing for new files/emails

### Frontend

- Timeline/Gantt: React plus vis-timeline, dhtmlxGantt, or similar
- Knowledge graph: Cytoscape.js, Sigma.js, Graphistry, or Neo4j Bloom
- Document viewer with highlighted citations
- Task/change approval inbox

---

## 7. MVP Plan

### Phase 0: Discovery and Data Audit

Goal: understand source material before building automation.

Tasks:

1. Inventory folder structure.
2. Count file types and sizes.
3. Sample 20-50 representative documents.
4. Identify naming conventions.
5. Identify version/revision patterns.
6. Identify important deliverables and contractual milestones.
7. Define security rules for cloud/local AI.

Output:

- data inventory
- source map
- document type taxonomy
- extraction difficulty score
- MVP scope

### Phase 1: Read-Only Document Ingestion

Goal: safely ingest documents without changing anything.

Build:

- file crawler
- metadata extractor
- checksum/deduplication
- document registry
- version tracking
- extracted text store
- citation references

Output:

- searchable document register
- document type classification
- basic full-text search

### Phase 2: RAG/Chat Over Project Documents

Goal: ask questions across the project archive with citations.

Build:

- chunking strategy
- embeddings
- vector database
- chat/query interface
- citation display
- source document links

Example questions:

- What are the current deliverables for the facade package?
- Who is responsible for fire safety documentation?
- What changed in the latest meeting minutes?
- Which deadlines are mentioned in the contract?
- Show all open action items from the last three meetings.

Output:

- project document Q&A with citations

### Phase 3: Structured Extraction

Goal: turn documents into project facts.

Extract:

- stakeholders
- deliverables
- dates
- action items
- obligations
- risks/issues
- decisions
- document references
- dependencies

Use schema validation:

- model proposes JSON
- validation checks required fields
- citations required for every claim
- low-confidence facts go to review

Output:

- structured project database
- initial knowledge graph
- initial timeline/task list

### Phase 4: Knowledge Graph

Goal: visualize how project facts connect.

Build graph around:

- people
- companies
- documents
- deliverables
- milestones
- obligations
- risks
- decisions
- tasks
- drawings/specs

Graph view should support:

- filter by package/discipline/date/person
- click node to see evidence
- path queries:
  - Why did this deadline move?
  - Which documents created this obligation?
  - Which tasks depend on this approval?
  - Which subcontractor is linked to this delay?

Output:

- browsable project knowledge graph

### Phase 5: Timeline and Task Automation

Goal: detect timeline/task updates from incoming material.

When new email/minute/document arrives:

1. classify source
2. extract candidate changes
3. compare against current project state
4. create proposed update with source evidence, confidence, and impact notes
5. require human approval for high-impact updates
6. apply to timeline/task system only after approval
7. log audit trail

Examples:

- Meeting minute says: Facade mockup postponed to 15 Sept.
  - system proposes milestone date change
  - links to meeting minute
  - flags affected dependent tasks
- Email says: John will send revised drawings by Friday.
  - system proposes new task for John
  - due date inferred
  - source email attached
- Contract says: Contractor must provide O&M documentation 10 business days before handover.
  - system creates obligation
  - calculates due date based on handover milestone

Output:

- living timeline
- task update proposals
- audit trail

### Phase 6: Integrations

Goal: connect to live project channels.

Possible connectors:

- email
- folders/SharePoint/Drive
- calendar/meeting minutes
- Procore/Dalux/Autodesk APIs
- MS Project/Primavera
- BIM/IFC model metadata
- task system

Output:

- automatic ingestion from real project channels

---

## 8. Human Approval Model

The system should not silently update project timelines at first.

Use three update modes:

### Mode 1: Suggest Only

- system proposes updates
- human approves/rejects
- safest for contracts/timelines

### Mode 2: Auto-Create Low-Risk Draft Tasks

- meeting action items become draft tasks
- user reviews daily digest

### Mode 3: Auto-Update Trusted Low-Risk Metadata

- only after confidence is proven
- only for low-risk metadata, such as file classification, document register fields, duplicate detection, and non-authoritative tags
- never for contract obligations, payment terms, deadlines, scope changes, safety decisions, liability conclusions, or real-person task assignments from ambiguous language

Every task, deadline, obligation, or graph fact should be able to answer:

> Where did this come from?

Every extracted fact should store:

- source document/email
- page/paragraph/email ID
- extraction timestamp
- model used
- confidence
- previous value if updated
- approval status
- approving user

---

## 9. Major Risks and Mitigations

### Risk 1: Bad OCR

Scanned PDFs and drawings may produce noisy text.

Mitigation:

- classify OCR quality
- use better OCR for critical docs
- keep citations visible
- require review for low-confidence extractions

### Risk 2: Version Confusion

Construction projects have many revisions.

Mitigation:

- detect document numbers/revisions
- model `supersedes` relationships
- do not treat old drawings/specs as current unless confirmed

### Risk 3: Hallucinated Obligations or Tasks

LLMs may infer too much.

Mitigation:

- structured extraction only
- require exact source citation
- confidence threshold
- human approval for contractual/timeline changes

### Risk 4: Email Thread Duplication

Same quoted email appears repeatedly.

Mitigation:

- thread parsing
- quote removal
- message ID tracking
- dedupe by content hash

### Risk 5: Permission Leakage

Not all users should see all documents/contracts.

Mitigation:

- preserve source permissions
- apply access control at query and graph level
- prevent RAG retrieval of unauthorized chunks

### Risk 6: Over-Building the Graph

A graph becomes useless if every sentence becomes a node.

Mitigation:

- start with project-management entities only
- avoid extracting everything
- prioritize decisions, obligations, deliverables, dates, risks, people, and documents

---

## 10. Recommended MVP Definition

Do not start with a fully automatic project brain.

Start with a read-only system that ingests one project folder, extracts text/metadata, builds a cited document Q&A layer, extracts deliverables/action items/dates from meeting minutes/contracts, and displays a draft timeline plus knowledge graph with human-approved updates.

### MVP Features

1. Folder crawler
2. Document register
3. Text/OCR extraction
4. RAG chat with citations
5. Meeting minute parser
6. Contract obligation parser
7. Deliverable/timeline extraction
8. Knowledge graph prototype
9. Timeline view
10. Human approval queue for proposed changes

### MVP Exclusions

- fully automatic timeline updates without approval
- deep drawing interpretation
- BIM object reasoning
- legal-grade contract interpretation
- multi-project enterprise permissions
- fine-tuning

---

## 11. Suggested Workstreams

### A. Data/Source Audit

- inventory files
- classify document types
- identify extraction difficulty
- sample representative documents locally without committing them

### B. Domain Model

- define project entities
- define graph schema
- define timeline/task schema
- define update/approval rules

### C. Extraction Pipeline

- PDF/DOCX/XLSX/email parsing
- OCR path
- document metadata
- citations

### D. AI Extraction

- prompt/schema design
- deliverables extraction
- obligation extraction
- action item extraction
- risk/issue extraction
- confidence scoring

### E. Storage/Search

- PostgreSQL
- graph database
- vector database
- document store
- audit log

### F. UI

- graph viewer
- timeline/Gantt
- document/citation viewer
- approval queue
- chat interface

### G. Integrations

- email
- folders/SharePoint/Drive
- calendar/meeting minutes
- existing task system

### H. QA/Governance

- evaluation set
- extraction accuracy tests
- human review process
- permission model
- privacy model

---

## 12. Recommended Default Path

Start with one project folder, read-only, local-first extraction, RAG with citations, meeting-minute action item extraction, contract obligation extraction, and a draft timeline/knowledge graph that requires human approval before updating anything.

This path creates useful value early while reducing the risks of hallucinations, privacy violations, and incorrect project-control decisions.

---

## 13. Next Discovery Checklist

Before implementation, answer:

1. Where are the project files stored?
2. What file types are most common?
3. Roughly how many files / how many GB?
4. Are scanned PDFs common?
5. Can data be sent to cloud LLMs, or must it stay local?
6. Do you already use Procore, Dalux, SharePoint, Teams, MS Project, Primavera, Autodesk Construction Cloud, or similar?
7. Should the first version be for one project only or many projects?
8. What is the most valuable first output?
   - knowledge graph
   - timeline
   - task extraction
   - contract obligation tracking
   - document Q&A
   - email/meeting update automation
