I want to rework the data quering and processing steps by adding onto what we already have: Instead of blinding quering all the APIs at our disposal when a company's data is requested we should have an orchestrating LLM that has a bank of our API resources at its disposal and prompts that let it understand what each API is good at (i.e apollo is good at sourcing contacts) and instructions that tell it to pick out the right tools to query for each data point that is required in the final output. The llm orchestrator should still pick multiple apis if possible, but it should ensure that the data point is actually accessible from the resource it is picking.

Heres how the new flow should work with new steps after a company is requested:
1. (NEW) Looking at the data points an orchestrator LLM assigns different apis for each data point (at least 2 api services for each data point still) - the data points that NEED to be outputted are as follows (MAKE SURE THESE ARE INCLUDED IN THE FINAL OUTPUT IN THE COMPANY OVERVIEW IF A DATAPOINT IS FULLY UNABLE TO BE FOUND, TEST ALL APIS AND THEN AS A LAST RESORT LEAVE IT AS NULL FOR NOW):

Executive Snapshot:
- Account name: [company name]
- Company overview: [Paragraph - AI generated overview of organization, who they are and what they do]
- Account type: [public/private sector]
- Industry: [Industry]
- Estimated Annual IT Budget: [Estimated annual IT spend: $X-YM]
- Installed technologies: [View software currently used - CRM, Marketing Automation, Sales Tools, Infrastructure, etc.] [If available, include the last seen date information]

Buying Signals:
- Top 3 Intent Topics: [Topic 1 Paragraph] [Topic 2 Paragraph] [Topic 3 Paragraph]
- Interest over time: [list of technologies the company is interested and the score indicating how interested they are with a paragraph summarizing everything]
- Top partner mentions: [List of associated vendors or keywords]
- Key Signals: [News and Triggers - 3 paragraphs based on news and a paragraph on what this means]

Opportunity Themes:
- Pain Points: [3 paragraph points]
- Sales Opportunities: [3 paragraph points where hp can sell to company]
- Recommended Solution Areas: [3 paragraph points based on pain points]

Stakeholder Map: Role Profiles for CIO / CTO / CISO / COO / CFO / CPO or other significant executives/ contacts - for each individual add:
- about: [1 paragraph bio - if they are a new hire call out and include date]
- strategic priorities [3 bullet points with descriptions]
- communications preferences:[Email / LinkedIn / Phone / Events]
- conversation starters: [1-2 sentences of persona-tailored language]
- recommended next steps: [Introduce emerging trends and thought leadership to build awareness and credibility/ Highlight business challenges and frame HP's solutions as ways to address them/ Reinforce proof points with case studies and demonstrate integration value/Emphasize ROI, deployment support, and the ease of scaling with HP solutions..4 points]

Supporting Assets: 
- add email template, linkedin outreach and call scripts for each contact

2. Querying APIs (SAME AS BEFORE, JUST NOW BASED ON ORCHESTRATOR)
- for paragraph output boxes use LLM to generate conclusions based on news from gnews api and also make sure to use chatgpt api to validate the news information (remember we are doing this from the perspective of hp trying to sellto the company that we are requesting so we need to determine if the information is relevant and valid)

3. LLM Council which aggregates everything and outputs the final data (basically same as before)

UPDATE THE PROCESS FLOW AND THE COMPANY OVERVIEW PAGES TO REFLECT THESE CHANGES, AS WELL AS ANY OTHER CONSIDERATIONS TO ENSURE THIS NEW REVAMPED VERSION WORKS MORE SMOOTHLY AND DISPLAYS ALL THE DATA WE NEED
