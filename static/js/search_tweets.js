import React, { Component } from 'react';
import axios from 'axios';


export default class Home extends Component {
   constructor(props) {
      super(props);
      this.state = { 
         images: [],
         searchTags: "",
         searchCount: 0
      }

      //event handlers
      this.handleTags = this.handleTags.bind(this);
      this.handleCount = this.handleCount.bind(this);

      //form submits
      this.searchTweets = this.searchTweets.bind(this);
   }
  

  
  
   searchTweets(e) {
    event.preventDefault();
    const tags = this.state.searchTags;
    const count = this.state.searchCount;

    console.log('submit');
    console.log(tags);
    console.log(count);
    axios.get('http://127.0.0.1:5000/twitter',
        {
          params: {
            tags: tags,
            count: count
          }
        })
      .then(res => {
        //message = res.data;
        console.log(res.data);
        const images = JSON.parse(res.data);
        this.setState({ images });
      })
  }

  handleTags(event) {
    this.setState({searchTags: event.target.value});
  }

  handleCount(event) {
    this.setState({searchCount: event.target.value});
  }

    render() {
       return (
         <div class="center">
            <h2>Photogamer</h2>
            <p>View photos published to Twitter for your favorite video games</p>
            <button type="button" onClick={this.hello}>Get Message</button>
            <button type="button" onClick={this.twitter}>Get Twitter</button>
            <form onSubmit={this.searchTweets}>
              <label>
                Hashtags:
                <input type="text" value={this.state.searchTags} onChange={this.handleTags} />
                <input type="text" value={this.state.searchCount} onChange={this.handleCount} />
              </label>
              <input type="submit" value="Submit" />
            </form>
           
           
           {this.state.images.map(image => <img src={image} width='100%'/>)}
         </div>
       )
    }
}

const domContainer = document.querySelector('#search_tweets_container');
ReactDOM.render(e(LikeButton), domContainer);
