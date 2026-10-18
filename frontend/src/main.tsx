/**
 * Entry point. The language catalog must be ready before any screen module is evaluated
 * (label maps call tr() at import time), so the app itself is imported after it.
 */
import { getLang, loadCatalog } from './i18n'

void loadCatalog(getLang()).finally(() => import('./boot'))
