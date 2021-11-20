import { randId, RANDOM_DEV_CODEVERSION_PREFIX } from './util'
import { loadSaveAndDump} from './build-corgi'

process.env['CODE_VERSION'] = process.env['CODE_VERSION'] ?? `${RANDOM_DEV_CODEVERSION_PREFIX}-${randId}`
loadSaveAndDump('./env/corgi-local.json', './corgi-local.yml')
