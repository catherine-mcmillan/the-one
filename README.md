# The ONE - Best of Finder

"The ONE" is a web application designed to help users find the best version of a product, recipe, or content across various websites like allrecipes.com, youtube.com, or etsy.com. The application analyzes ratings and user comments to provide you with the most highly-rated options.

## Features

- Search through popular websites to find the best products, recipes, tutorials, etc.
- Choose between simple or detailed search results
- View detailed summaries of user comments, including pros, cons, and tips
- Get insights into why a particular item is considered "the best" based on collective user feedback
- Engaging loading page with progress updates and fun messages during search
- Background processing for long-running searches

## Technologies Used

- Python 3.9
- Flask web framework
- Firecrawl API for web scraping and data extraction
- Bootstrap for responsive design
- Pydantic for data validation
- Deployed on Fly.io

## Installation and Setup

### Prerequisites

- Python 3.9 or higher
- Conda or another virtual environment manager
- Firecrawl API key (get one at [Firecrawl](https://docs.firecrawl.dev/))

### Local Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/the-one.git
   cd the-one
   ```

2. Create a Conda environment:
   ```bash
   conda create -n the_one python=3.9
   conda activate the_one
   ```

3. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the project root with the following contents:
   ```
   SECRET_KEY=your-secret-key-here
   FIRECRAWL_API_KEY=your-firecrawl-api-key-here
   FLASK_APP=run.py
   FLASK_ENV=development
   ```

5. Run the Flask application:
   ```bash
   flask run
   ```

6. Access the application at `http://127.0.0.1:5000`

## Usage

1. On the homepage, enter the website you want to search (e.g., allrecipes.com)
2. Enter your search query (e.g., "chocolate chip cookies")
3. Select your search type:
   - Simple Search: Quick results with basic information
   - Detailed Search: Comprehensive results with user feedback analysis
4. Click "Find The ONE" to start your search
5. Watch the progress bar and fun messages while the search completes
6. Browse through the results to find the best option for your needs

## Search Process

- Simple searches typically take 1-2 minutes
- Detailed searches with user feedback analysis may take 2-3 minutes
- Progress bar and countdown timer show estimated completion time
- Fun messages keep you entertained during the search
- Results are automatically displayed when ready

## Testing

Run the test suite with:

```bash
./run_tests.sh
```

or

```bash
python -m pytest -v
```

## Deployment

The application is configured for deployment on Fly.io. See the Deployment section below for instructions.

## API Documentation

This application uses the Firecrawl API for web scraping and data extraction. For more information about the API, visit:
- [Firecrawl Documentation](https://docs.firecrawl.dev/)
- [API Introduction](https://docs.firecrawl.dev/introduction)

## License

This project is licensed under the MIT License - see the LICENSE file for details.