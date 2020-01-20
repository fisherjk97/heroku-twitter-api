'use strict';

const e = React.createElement;
const axios = require('axios');
class LikeButton extends React.Component {
  constructor(props) {
    super(props);
    this.state = { liked: false };
  }





  render() {
    
    if (this.state.liked) {
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

    return e(
      'button',
      { onClick: () => this.setState({ liked: true }) },
      'Like'
    );
  }
}

const domContainer = document.querySelector('#search_button_container');
ReactDOM.render(e(LikeButton), domContainer);