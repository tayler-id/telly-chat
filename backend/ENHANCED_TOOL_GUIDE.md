# Enhanced YouTube Tool Guide

The enhanced YouTube tool provides intelligent content analysis with automatic detection of video types and AI-generated content.

## Features

### 1. Content Type Detection
Automatically detects the type of video:
- **Tutorial** - Step-by-step guides and how-to videos
- **News** - Breaking news and current events
- **Review** - Product/service reviews
- **Educational** - Academic and learning content
- **Entertainment** - Comedy, vlogs, etc.
- **Music** - Music videos and performances
- **Documentary** - In-depth explorations
- **Podcast** - Interview and discussion format
- **Other** - General content

### 2. AI-Generated Content Detection
Identifies potentially AI-generated videos by analyzing:
- Speech patterns and phrasing
- Content structure
- Language naturalness
- Personal elements vs generic templates

### 3. Adaptive Output Generation
Different video types get different analysis formats:

#### Tutorials
- Overview of what will be learned
- Prerequisites
- Step-by-step instructions
- Tips & best practices
- Common issues and solutions

#### News
- Headline summary
- Key points (bullet list)
- Detailed summary
- Context and background
- Implications

#### Reviews
- Product/service being reviewed
- Overall verdict
- Pros and cons lists
- Key features discussed
- Recommendations

#### Educational
- Main topic
- Key concepts explained
- Important points
- Examples given
- Summary and further learning

## Usage

### In Chat
Simply paste a YouTube URL and the tool will:
1. Extract the transcript
2. Detect the content type
3. Check for AI-generated content
4. Generate appropriate analysis

Example:
```
User: https://www.youtube.com/watch?v=dQw4w9WgXcQ
Assistant: [Detects music video, provides appropriate analysis]
```

### Via API
```bash
POST /youtube/process?url=https://youtube.com/watch?v=...
```

Response includes:
- Content type
- AI-generated flag
- Type-specific analysis
- Full transcript (saved)

## Testing

### Test Content Detection
```bash
python test_content_detection.py
```

### Test with Real Videos
```bash
python test_enhanced_tool.py [optional-youtube-url]
```

## Configuration

The tool uses the configured LLM (Anthropic Claude or OpenAI) for analysis.
Set in `.env`:
```
MODEL_PROVIDER=anthropic
ANTHROPIC_API_KEY=your-key
```

## How It Works

1. **Transcript Extraction** - Uses Telly agent to get video transcript
2. **Content Analysis** - LLM analyzes title + transcript excerpt
3. **Type Detection** - Identifies content category
4. **AI Detection** - Checks for AI-generated patterns
5. **Output Generation** - Creates type-specific summary

## Benefits

- **Better User Experience** - Get relevant information based on video type
- **AI Awareness** - Know when content might be AI-generated
- **Structured Output** - Consistent, useful formats
- **Smart Summaries** - Type-appropriate analysis

## Examples

### Tutorial Detection
Video: "How to Build a React App"
Output: Step-by-step guide with prerequisites and tips

### News Detection
Video: "Breaking: Tech Company Layoffs"
Output: Key points, summary, and implications

### AI-Generated Detection
Video: Generic content with robotic patterns
Output: Warning flag + analysis