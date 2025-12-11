# Netlify Deployment Guide

## Prerequisites
- GitHub account with the code pushed to a repository
- Netlify account (free tier works)
- Python 3.8+

## Local Testing

Before deploying, test the Streamlit app locally:

```bash
pip install -r requirements.txt
streamlit run app.py
```

The app will be available at `http://localhost:8501`

## Deployment Steps

### 1. Push Code to GitHub

```bash
git init
git add .
git commit -m "Initial commit: Invoice to Tally Converter"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/tally-connector.git
git push -u origin main
```

### 2. Connect to Netlify

1. Visit [netlify.com](https://netlify.com)
2. Click "Sign up" and authenticate with GitHub
3. Click "New site from Git"
4. Select your GitHub repository
5. Configure build settings:
   - **Build command:** `pip install -r requirements.txt && streamlit run app.py --logger.level=debug`
   - **Publish directory:** Leave blank
   - **Functions directory:** `functions`
6. Click "Deploy site"

### 3. Environment Variables

If using a `.env` file with sensitive credentials:

1. In Netlify dashboard, go to **Site settings** → **Build & deploy** → **Environment**
2. Add your environment variables (API keys, etc.)

Example variables:
```
DEEPINFRA_API_KEY=your_key_here
```

### 4. Configure for Streamlit

Streamlit requires special configuration for Netlify. The `netlify.toml` file is already configured, but you may need to adjust:

- **File:** `netlify.toml`
- **Key settings:** Build command, function directory, redirects

## Known Limitations

Streamlit apps on Netlify have limitations:
- File uploads are limited to the upload size configured in `.streamlit/config.toml` (default: 200MB)
- Session state resets when the page refreshes
- Real-time features work best with WebSocket support

## Troubleshooting

### Build Fails
- Check the Netlify build logs for errors
- Ensure all dependencies are in `requirements.txt`
- Verify Python version compatibility

### App Won't Load
- Check browser console for errors
- Verify API credentials in environment variables
- Ensure CORS headers are properly set

### Upload Issues
- Check the file size limit in `.streamlit/config.toml`
- Verify file format (PNG, JPG, JPEG, PDF)

## Alternative: Use Streamlit Cloud (Recommended)

For better Streamlit support, consider using Streamlit Cloud:

1. Push code to GitHub
2. Visit [share.streamlit.io](https://share.streamlit.io)
3. Click "New app"
4. Select your repository and branch
5. Streamlit handles deployment automatically

## Support

For issues:
- Streamlit docs: https://docs.streamlit.io
- Netlify docs: https://docs.netlify.com
- GitHub Issues: Open an issue in your repository
