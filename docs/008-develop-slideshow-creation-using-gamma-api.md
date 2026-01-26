```markdown
# Slideshow Creation Feature Using Gamma API

## Overview
This document provides instructions for implementing the feature that creates prompts from company data, formats them as markdown files, and sends them to the Gamma API to generate slideshows.

## Feature Details

### Data Source
- **Table**: `finalize-data`
- **Purpose**: Source of company data for slideshow prompts.

### Markdown Formatting
- Create a markdown template to structure the slideshow prompts.
- Ensure that data from `finalize-data` is accurately inserted into the markdown.

### Gamma API Integration
- **Purpose**: To generate slideshows from markdown prompts.
- **Authentication**: Ensure appropriate authentication credentials are in place.
- **Endpoint**: Consult Gamma API documentation for the specific endpoint used for slideshow generation.

### Implementation Steps
1. **Data Retrieval**: Query the `finalize-data` table for necessary information.
2. **Markdown Creation**: Format the retrieved data into a pre-defined markdown template.
3. **API Request**: Send the markdown file to Gamma API using a POST request.
4. **Response Handling**: Check API responses for success or errors and handle accordingly.

### Error Handling
- Validate all data before processing to ensure accuracy.
- Implement retry logic for API request failures.
- Log errors for debugging and analysis.

### Testing
- Write and run unit tests for markdown formatting.
- Conduct integration tests to ensure successful API interaction and slideshow generation.
- Validate the content of generated slideshows against the source data.

## Usage Instructions
1. **Prepare Environment**: Ensure necessary libraries and credentials for Gamma API are installed and configured.
2. **Execute Feature**: Run the script to process data and generate slideshows.
3. **Verify Outputs**: Check the generated slideshows for accuracy and completeness.

## Dependencies
- **Python**: For script execution
- **SQL Database**: Source data retrieval
- **Gamma API**: Slideshow generation endpoint

## Notes
- Ensure markdown files adhere to the structure required by Gamma API.
- Regularly update authentication credentials for secure API access.
```
