import React, { Component } from 'react';
import NavBar from './components/NavBar'
import VisGraph from './components/VisGraph'
import './App.css';

class App extends Component {
  render() {
    return (
      <div id="content">
        <NavBar />
        <VisGraph />
      </div>
    );
  }
}

export default App;