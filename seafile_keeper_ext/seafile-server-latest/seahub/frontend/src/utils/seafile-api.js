import cookie from 'react-cookies';
import { SeafileAPI } from 'seafile-js';
import { KeeperAPI } from './keeper-api'
import { siteRoot } from './constants';

let seafileAPI = new SeafileAPI();
let keeperAPI = new KeeperAPI();
let xcsrfHeaders = cookie.load('sfcsrftoken');
seafileAPI.initForSeahubUsage({ siteRoot, xcsrfHeaders });
keeperAPI.initForSeahubUsage({ siteRoot, xcsrfHeaders });

export { seafileAPI, keeperAPI };
