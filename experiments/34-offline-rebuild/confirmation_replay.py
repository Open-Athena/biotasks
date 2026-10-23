"""Reuse frozen replay unchanged except this attempt's resource ownership."""
import replay_macs_742_image as replay

replay.OWNER = 'biotasks34-macs-742-confirm-001-image'
replay.LABEL = 'org.open-athena.biotasks.owner=' + replay.OWNER
replay.TAG = replay.OWNER + ':recorded-actions'
replay.REPORT['run_id'] = replay.OWNER

if __name__ == '__main__':
    replay.main()
