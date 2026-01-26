The Stack:  

Frontend: React/ Next.js à web-app which the user will interact with to query 

Backend: FastAPI à enables usage of Python libraries to make processing easier 

Database: Supabase à tables from which data is injected and pulled 

The Process: 

Workflow Start: User requests a profile for a specific company on the frontend, which triggers a request for the Python backend. Backend then sends a POST request to an n8n webhook with the company requested formatted in a JSON file. 

Data Retrieval Step: 

1. Programmatic Orchestration (The Trigger) The core backend monitors for new data requests (e.g., a new list of target companies). Instead of processing these on the main server, it sends a mutation request to the Railway.app GraphQL API. 

Action: This API call triggers the deployment of a specialized, isolated "Extractor Container." 

Benefit: Decouples heavy API I/O operations from the main application, preventing latency and ensuring 100% uptime for user-facing features. 

2. Ephemeral Worker Deployment Railway provisions a dedicated environment for the extraction task. This worker service is spun up instantly, specifically configured with the necessary secrets and environment variables to communicate with external vendors. 

3. Parallelized Intelligence Gathering Once active, the worker executes high-throughput, asynchronous requests to external intelligence sources: 

Apollo.io: Retrives firmographic data, contact information, and funding history. 

PeopleDataLabs (PDL): Aggregates workforce analytics, social footprint, and talent density metrics. 

4. Raw Data Handoff (Supabase Injection) The worker compiles the raw JSON responses from these providers and injects them directly into the Supabase "raw-data" table. 

Completion: Once the batch extraction is complete and the data is safely stored, the worker service reports success and can be programmatically spun down to save costs. 

Data Validation: Data validation will be conducted by LLM agents as Python iterates through each JSON element of the “staging-normalized” Supabase table by considering 1 of 3 cases: 

CASE 1: All data provided by each API data provider is the same! 

No changes are necessary, the final data value is the one that is constant 

CASE 2: Conflicting data values are provided by different API services 

We would use a council of LLMs to assign different weight scores to each API provider and a revolver as the “leader” of this council to determine which data point is the most accurate 

CASE 3: NULL data available 

In this case use a headless browser API like Firecrawl to scrape for the required data while bypassing proxies and CAPTCHAS 

Backup AI council that can select from an arsenal of tools 

After finalizing the proper data points for each required this is pushed into a Supabase table "finalize- data” 

Slideshow Creation: Create prompts using Python, word doc template and “finalize-data” Supabase table and feed those prompts into Gamma API to generate the final slideshow with all the company information and details à prompts will be formatted as a markdown file which Gamma API can read 

 

Resolution (Council of LLMs + Revolver) Logic 

Inputs 

For each standardized field (e.g. employee count, headquarters, communication preference, etc.), the inputs are: 

A list of candidate values from the sorting stage 

Metadata for each, including: 

Data source 

Source reliability level 

Timestamp 

Flow 

Evidence: A council of LLM agents (around 10-20) evaluates candidates based on the inputs listed above à however they do not make final decisions; rather they provide signals 

Final Decision: a “council leader” or revolver agent consolidates all these signals from the council and applies predefined resolution rules to determine: 

A confidence score 

A winner (if high enough confidence value) 

Alternative values ranked 

A list of rules applied (audit) 

 

Resolution Rules 

Criteria for evaluation: 

Source Reliability: sources are assigned a tier based on a source, with higher tiers having greater weight 

Cross-source Agreement: a value is preferred if provided independently by multiple sources 

Field Type: 

Values are compared according to data type: 

Numeric fields (e.g., employee count) allow small differences and are treated as the same if values are close 

Text fields value clearer, more complete descriptions 

Identity fields (e.g., CEO name) require stronger and more consistent evidence 

Recency: more recent values are preferred 

 

Outputs 

The final decision (confidence score, winner if high enough confidence value, alternative values ranked, and a list of rules applied) will be outputted by the system and written to the Supabase table to be further processed. 