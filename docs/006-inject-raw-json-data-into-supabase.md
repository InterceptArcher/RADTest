```markdown
# Technical Specification: Inject Raw JSON Data into Supabase

## Summary
The objective is to implement a feature that allows a worker to compile data from external sources and inject this compiled JSON data directly into the Supabase 'raw-data' table. This will involve formatting the JSON data correctly and ensuring it is inserted successfully into the database.

## Implementation Steps

1. **Data Compilation**:
   - Develop a worker function to gather data from predefined external sources.
   - Ensure data is collected in JSON format and complies with the structure required by the 'raw-data' table.

2. **Data Formatting**:
   - Create a validation layer to check JSON structure against Supabase 'raw-data' table schema.
   - Implement error handling to catch and log formatting issues.

3. **Supabase Integration**:
   - Set up the connection to the Supabase database using appropriate authentication methods (e.g., API keys, service roles).
   - Use Supabase client libraries to facilitate database operations.

4. **Data Insertion**:
   - Implement a function to insert validated JSON data into the 'raw-data' table.
   - Ensure the function handles batch inserts for efficiency if multiple records are compiled at once.

5. **Testing and Validation**:
   - Write unit tests to cover data compilation, validation, and insertion processes.
   - Perform integration testing to verify end-to-end functionality from data compilation to successful insertion in Supabase.

6. **Deployment**:
   - Deploy the worker functionality to the appropriate environment.
   - Monitor logs to ensure data is being injected correctly and efficiently.

## Tech Stack

- **Node.js**: For implementing the worker function and handling asynchronous operations.
- **Supabase**: As the database service for storing raw JSON data.
- **Supabase JS Client**: For database operations and integration.
- **Jest/Mocha**: For testing the functionality and ensuring reliability.
- **Docker**: To containerize the worker for consistent deployment environments.

## Edge Cases

- **Network Failures**: Implement retry logic for network-related failures during data fetching or insertion.
- **Data Inconsistencies**: Handle cases where external data might be incomplete or malformed, ensuring such records are logged and skipped.
- **Authentication Issues**: Ensure robust error handling for authentication failures when connecting to Supabase.
- **Rate Limiting**: Consider Supabase's rate limits for data insertion and plan batch sizes accordingly.
```
