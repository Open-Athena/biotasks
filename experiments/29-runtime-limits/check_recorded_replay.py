"""Shell-state and stop-boundary fixtures; no repository replay or Docker."""
import hashlib,json,subprocess,tempfile,time
from pathlib import Path
from types import SimpleNamespace
from recorded_replay import replay_recorded_actions
ROOT=Path(__file__).resolve().parent


def actions(commands):
    return [{'step':i,'command':command,'command_sha256':hashlib.sha256(command.encode()).hexdigest(),
             'expected_exit_code':code,'timeout_seconds':300} for i,(command,code) in enumerate(commands)]


def main():
    results=[]
    with tempfile.TemporaryDirectory(prefix='biotasks29-replay-') as td:
        root=Path(td)
        class Local:
            def exec(self,command,*,timeout):
                start=time.monotonic();p=subprocess.run(['bash','-lc',command],cwd=root,capture_output=True,text=True,timeout=5)
                return SimpleNamespace(exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr,duration_sec=time.monotonic()-start)
        # Failed actions can mutate state which later recorded commands consume.
        report=replay_recorded_actions(Local(),actions([('printf retained > state; false',1),('test "$(cat state)" = retained && printf yes > continued',0)]),root/'matched')
        assert report['status']=='matched_recorded_exits' and (root/'continued').read_text()=='yes'
        results.append({'case':'expected_failure_preserves_state_and_continues','status':report['status'],'steps':len(report['steps'])})
        report=replay_recorded_actions(Local(),actions([('echo bad <',2),('printf yes > after_syntax',0)]),root/'syntax')
        assert report['status']=='matched_recorded_exits' and (root/'after_syntax').exists()
        results.append({'case':'expected_syntax_error_continues','status':report['status'],'steps':len(report['steps'])})
        report=replay_recorded_actions(Local(),actions([('false',0),('touch must_not_exist',0)]),root/'divergence')
        assert report['status']=='exit_code_divergence' and report['unstarted_steps']==[1] and not (root/'must_not_exist').exists()
        results.append({'case':'unexpected_exit_stops','status':report['status'],'steps':len(report['steps'])})
        class Timeout:
            def exec(self,command,*,timeout):return SimpleNamespace(exit_code=124,stdout='partial',stderr='timeout',duration_sec=0)
        report=replay_recorded_actions(Timeout(),actions([('true',0),('true',0)]),root/'timeout')
        assert report['status']=='client_timeout_remove_sandbox' and report['unstarted_steps']==[1]
        results.append({'case':'synthetic_client_timeout_stops','status':report['status'],'steps':len(report['steps'])})
        class Error:
            def exec(self,command,*,timeout):raise OSError(7,'synthetic argument limit')
        report=replay_recorded_actions(Error(),actions([('true',0),('true',0)]),root/'exception')
        assert report['status']=='executor_exception' and report['unstarted_steps']==[1]
        results.append({'case':'executor_exception_stops','status':report['status'],'steps':len(report['steps'])})
    output={'scope':'Two real Bash state/continuation fixtures, actual divergence, synthetic timeout/exception boundaries',
            'cases':results,'all_assertions_passed':True,'temporary_directory_removed':not root.exists(),
            'limits':['No Docker or original repository replay','No remote cancellation, image reconstruction or readiness established']}
    (ROOT/'recorded-replay-check.json').write_text(json.dumps(output,indent=2)+'\n');print(json.dumps(output))


if __name__=='__main__':main()
