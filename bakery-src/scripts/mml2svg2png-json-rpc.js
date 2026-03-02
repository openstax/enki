/* global MathJax:true */

// How to run server manually:
// node -r esm mml2svg2png-json-rpc.js
//
// How to run server with pm2:
// pm2 start mml2svg2png-json-rpc.js --node-args="-r esm" --wait-ready --listen-timeout 8000

// listen port
const listenPort = 33001

//
// Mathjax options
//
const mjopt = {}
mjopt.inline = false // process as inline math
mjopt.em = 16 // em-size in pixels
mjopt.ex = 8 // ex-size in pixels
mjopt.width = 80 * 16 // width of container in pixels
mjopt.fontCache = true
mjopt.assistiveMml = false
mjopt.dist = false

//
// Configure MathJax
//
MathJax = {
     options : {
          enableAssistiveMml : mjopt.assistiveMml,
          enableEnrichment : true, // false to disable enrichment
          sre: {
               speech : 'shallow' // options: 'none', 'shallow', or 'deep'
          }
     },
     loader : {
          paths : {
               mathjax : 'mathjax-full/es5'
          },
          source : (mjopt.dist ? {} : require('mathjax-full/components/src/source.js').source),
          require : require,
          load : [ 'adaptors/liteDOM', 'input/mml/entities', 'a11y/semantic-enrich' ]
     },
     startup : {
          typeset : false
     },
     svg : {
          fontCache : (mjopt.fontCache ? 'local' : 'none')
     }
}

//
//  Load the startup modules
//
require('mathjax-full/' + (mjopt.dist ? 'es5' : 'components/src/mml-svg') + '/mml-svg.js')
const sharp = require('sharp')

//
//  Wait for MathJax to start up, and then typeset the math
//
MathJax.startup.promise.then(() => {
     const jayson = require('jayson')
     
     // create a server
     const server = jayson.server({
          mathml2svg : function (args, callback) {
               MathJax.mathml2svgPromise(args[0] || '', {
                    display : !mjopt.inline,
                    em : mjopt.em,
                    ex : mjopt.ex,
                    containerWidth : mjopt.width
               }).then((node) => {
                    const adaptor = MathJax.startup.adaptor
                    const speech = adaptor.getAttribute(node, 'aria-label')
                    const html = adaptor.outerHTML(node)
                    // output as svg and mathspeak from aria-label
                    callback(null, [html, speech])
               }).catch((err) => {
                    console.log(err)
                    callback(null, [ '', '' ]) // return empty string array for predictable error handling in python
               })
          },
          svg2png : function (args, callback) {
               const svgBuffer = Buffer.from(args[0])
               sharp(svgBuffer, {
                    density : 900
               }) // density describes DPI
                   .png()
                   .toBuffer()
                   .then(data => {
                        callback(null, data.toString('base64'))
                   })
                   .catch(err => {
                        console.log(err)
                        callback(null, '')
                   })
          }
     })
     
     server.http().listen(listenPort, () => {
          console.log('Listening on *:' + listenPort)
          // If running with PM2 (try/catch block) we send ready signal to PM2
          try {
               process.send('ready')
          } catch (err) {
               // do nothing because not running with PM2
          }
     })
}).catch(err => console.log(err))
