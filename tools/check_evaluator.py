import json,sys,tempfile,threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'culture_diversity/benchmark'))
from culture_eval_benchmark.evaluator import BenchmarkEvaluator
class Judge(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_POST(self):
  self.rfile.read(int(self.headers['Content-Length']));data=json.dumps({'choices':[{'message':{'content':json.dumps({'score':0,'reason':'fixed protocol fixture, not a real judgment'})}}]}).encode();self.send_response(200);self.end_headers();self.wfile.write(data)
server=ThreadingHTTPServer(('127.0.0.1',0),Judge);threading.Thread(target=server.serve_forever,daemon=True).start()
try:
 with tempfile.TemporaryDirectory() as d:
  model={'api_base':f'http://127.0.0.1:{server.server_port}/v1','model':'fixture','api_key':'','retries':0,'timeout':5}
  config={'project_root':str(ROOT),'dataset':{'path':'examples/fictional.jsonl'},'output_dir':d+'/output','target':{'type':'dataset_reference'},'judges':{'ethnic_group_judge':model,'cultural_difference_judge':model,'cultural_difference_prompt_path':'culture_diversity/benchmark/prompts/cultural_difference_judge.txt'}}
  path=Path(d)/'config.json';path.write_text(json.dumps(config));BenchmarkEvaluator(path).run()
  assert (Path(d)/'output/summary.json').is_file();assert (Path(d)/'output/sample_results.jsonl').is_file()
  rows=[json.loads(x) for x in (Path(d)/'output/sample_results.jsonl').read_text().splitlines() if x.strip()];assert len(rows)==1 and rows[0]['composite_score']==0
  print('full evaluator with local fixed-zero judge: passed; no real model evaluation')
finally:server.shutdown();server.server_close()
