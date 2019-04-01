import React from 'react';
import ReactDOM from 'react-dom';
import { HashRouter } from 'react-router-dom';
import './index.scss';
import "@babel/polyfill";
import App from './App';
import { SnackbarProvider } from 'notistack';
//import registerServiceWorker from './registerServiceWorker';

ReactDOM.render(<HashRouter>
    <SnackbarProvider maxSnack={3}>
    <App />
    </SnackbarProvider>
    </HashRouter>, document.getElementById('root'));
//registerServiceWorker();