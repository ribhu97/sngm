"""Start the local-only backend; provider selection happens before app construction."""
import argparse
import os
import uvicorn
from dotenv import load_dotenv

if __name__ == '__main__':
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument('--provider', choices=['elevenlabs','lfm3','rehearsal'],default=os.getenv('SNGM_PROVIDER','elevenlabs'))
    parser.add_argument('--port',type=int,default=8000)
    parser.add_argument('--lfm3-url',default=os.getenv('LFM3_BASE_URL','http://127.0.0.1:9931'))
    args = parser.parse_args()
    os.environ['LFM3_BASE_URL'] = args.lfm3_url
    from app.api import create_app
    uvicorn.run(create_app(provider=args.provider),host='127.0.0.1',port=args.port)
