import urllib.request
import urllib.error
from pathlib import Path
from loguru import logger

def generate_from_kroki(diagram_type: str, code: str, output_path: str) -> bool:
    """
    Generate an image from text-based diagram code using the Kroki API.
    
    Args:
        diagram_type: The type of diagram (e.g., 'mermaid', 'plantuml', 'excalidraw').
        code: The raw text code for the diagram.
        output_path: The local path where the generated PNG should be saved.
        
    Returns:
        bool: True if successful, False otherwise.
    """
    url = f"https://kroki.io/{diagram_type}/png"
    
    # Kroki expects raw text for POST /:dsl/:format
    data = code.encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "text/plain; charset=utf-8")
    req.add_header("User-Agent", "BloggerAgent/1.0 (https://github.com/BlackwaterTechnology/blogger-agent)")
    
    try:
        logger.info(f"Requesting diagram rendering from kroki.io for type '{diagram_type}'...")
        
        # Create unverified context to prevent macOS SSL certificate issues
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        with urllib.request.urlopen(req, context=ctx) as response:
            if response.status == 200:
                out_file = Path(output_path)
                # Ensure parent directories exist
                out_file.parent.mkdir(parents=True, exist_ok=True)
                
                with open(out_file, "wb") as f:
                    f.write(response.read())
                logger.success(f"Diagram successfully generated and saved to {output_path}")
                return True
            else:
                logger.error(f"Kroki API returned status {response.status}")
                return False
                
    except urllib.error.HTTPError as e:
        logger.error(f"HTTP Error rendering diagram: {e.code} - {e.reason}")
        # Sometimes Kroki returns the error message in the body
        try:
            error_body = e.read().decode("utf-8")
            logger.error(f"Kroki response: {error_body}")
        except:
            pass
        return False
    except Exception as e:
        logger.error(f"Failed to generate diagram: {str(e)}")
        return False
