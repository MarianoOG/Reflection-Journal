# Reflection Journal

This repository is an app to a systematic approach to understanding life, making better decisions, and continuously improving. It represents my journey of personal growth and philosophical exploration.

## Core Components

1. **Self-Reflection Engine**
   - **Reflections**: Capture thoughts based on questions that you create.
   - **Analize your thoughts**: LLM-assisted analysis of your reflexion entries.
   - **Challenge Questions**: LLM-assisted questioning of your assumptions, blind-spots and contradictions.

2. **Review System**
   - **Insights**: LLM-assisted analysis of reflection entries to identify patterns.
   - **Goal Definition**: Create and review goals based on what is important for you based on the insights.
   - **Task Generation**: Convert goals into actionable tasks.

## Technical Stack

- **App**: Streamlit for interactive interfaces
- **Infrastructure**: GCP Cloud Run for containerized services
- **Storage**: File System for Reflexion Entries and Questions
- **Third Party APIs**: OpenAI for LLM integration

## Getting Started

1. **Prerequisites**
   - OpenAI API key
   - Bucket in GCP

3. **Local Development**
   ```bash
   # Install dependencies
   cd src && pip install -r requirements.txt

   # Run services
   cd ../src
   streamlit run main.py --server.port 8080
   ```

4. **Deployment**
   - Automated deployment is configured via GitHub Actions
   - Workflow configuration is in [.github/workflows/deploy.yml](.github/workflows/deploy.yml)
   - Requires GCP credentials configured as repository secrets

## Configuration

Create a [`.env`](.env) file with the following:
```
OPENAI_API_KEY=your_openai_key
BUCKET_NAME=your_google_cloud_service_bucket
```

## Contributing

You can contribute to the project by adding new features or fixing bugs.

## License

MIT License - see LICENSE file for details
