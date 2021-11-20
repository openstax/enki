import { randId, RANDOM_DEV_CODEVERSION_PREFIX } from './util'
import { loadSaveAndDump} from './build-webhosting'

process.env['CODE_VERSION'] = process.env['CODE_VERSION'] ?? `${RANDOM_DEV_CODEVERSION_PREFIX}-${randId}`
loadSaveAndDump('./env/webhosting-local.json', './webhosting-local.yml')
