// adapted from https://stackoverflow.com/questions/59421516/is-there-a-non-blocking-http-client
package main

import (
	"bytes"
	"encoding/base64"
	b64 "encoding/base64"
	"flag"
	"fmt"
	"io/ioutil"
	"log"
	"net/http"
	"os"
	"strings"
	"sync"
	"sync/atomic"
	"time"

	"github.com/sbinet/npyio/npy"
)

// TODO: change to user config
var IP string
var APP string
var URL string

/*COMPLICATED load generation*/
// type httpResp struct {
//     Response *http.Response
//     Error    error
// }

// const numRequests = 2

// type User struct {
//     req_rate float64 //in rps
//     duration float64 //in seconds (int-only)
// }

// func (user User) genReq(rc chan httpResp) {
//     resp, err := http.Get("http://example.com")
//     rc <- httpResp{
//         Response: resp,
//         Error:    err,
//     }
// }

// func (user User) handleResponse(rc chan httpResp, wg *sync.WaitGroup) {

//     for get := range rc {

//         if get.Error != nil {
//             log.Println(get.Error)
//         } else {
//             log.Println(get.Response.Status)
//         }
//         wg.Done()
//     }

// }

// func (user User) StartLoad() {
//     actual_duration := time.Second * time.Duration(user.duration * rand.ExpFloat64())
//     interval := time.Duration(1e9*(1/user.req_rate))*time.Second
//     cur := time.Now()
//     numRequests := int(user.req_rate * float64(actual_duration))
//     rc := make(chan httpResp, numRequests)
//     wg := &sync.WaitGroup{}
//     for cur.Before(time.Time.Add(cur,actual_duration)) {
//         wg.Add(1)
//         go user.genReq(rc)
//         time.Sleep(interval)
//     }

//     go HandleResponse(rc, wg)
//     wg.Wait()
// }

type nonBlocking struct {
	e2e      time.Duration
	Response *http.Response
	Error    error
}

func main() {
	lflag := flag.Int("limit", 42, "an int")
	duration := flag.Int("duration", 60, "duration (in seconds)")
	tracefile := flag.String("trace", "./traffic_dur1000_lam1.0_stime10.0_rate1.0_site1.npy", "Trace file for load generation")
	ipstr := flag.String("host", "192.168.10.10:9696", "offload daemon host IP")
	appstr := flag.String("app","fibtest", "application to send requests to")
	qpsptr := flag.Int("qps", 0, "qps (queries per second)")
	minuteptr := flag.Int("minute", 0, "minute to start the experiment in the trace")

	flag.Parse()
	limit := *lflag
	qps := *qpsptr
	IP = *ipstr
	APP = *appstr
	minute := float64(*minuteptr)



	//limit := 10
	f, err := os.Open(*tracefile)
	if err != nil {
		log.Printf("error reading file")
	}
	var data []float64
	err = npy.Read(f, &data)

	if err != nil {
		log.Printf("error parsing numpy data")
	}

	nb := make(chan nonBlocking, limit)
	wg := &sync.WaitGroup{}

	var curImageBytes, prevImageBytes string
	switch APP {
	case "fibtest":
		template := "http://%s/api/v1/namespaces/guest/actions/%s?blocking=true&result=true"
		go HandleResponse(nb, wg)
	case "video_analytics_pipeline":
		template := "http://%s/api/v1/namespaces/guest/dag/%s?blocking=true&result=true"
		logItems := []string{
			"0.0ms", "0.0ms", "0.0ms", "0.0ms", "0.0ms", "0.0ms", "0.0ms", "0.0ms", "0.0ms", "0.0ms", "0.0ms", "0.0ms", "0.0ms",
			time.Now().Format("15:04:05.000"),
		}
		fmt.Println(strings.Join(logItems, ","))
		curImageBytes = encodeImage("/tmp/imgs/out002.jpg")
		prevImageBytes = encodeImage("/tmp/imgs/out001.jpg")
		go HandleResponseVideo(nb, wg)
	}

	URL = fmt.Sprintf(template, IP, APP)
	var start time.Time
	secPtr := 0.0
	checkPtr := true

	var sleep_ms int
	if qps != 0 {
		start = time.Now()
		checkPtr = false
		sleep_ms = 1000 / qps
	}
	for i, d := range data {

		// if i >= limit {
		// 	break
		// }

		// log.Print(d)
		// log.Print(minute)

		if checkPtr {
			secPtr += d
			if (secPtr < minute * 60) {
				continue
			} else {
				log.Printf("Starting the traffic generation at second %f",secPtr)
				start = time.Now()
				checkPtr = false
			}
		}

		if time.Since(start).Seconds() >= float64(*duration) {
			break
		}

			wg.Add(1)
			switch APP {
			case "fibtest":
				go Request(nb)
			case "video_analytics_pipeline":
				go RequestVideo(nb, curImageBytes, prevImageBytes)
		}
		if qps == 0 {
			time.Sleep(time.Duration(d*1e9) * time.Nanosecond)
		} else {
			time.Sleep(time.Duration(sleep_ms) * time.Millisecond)
		}
		i++
	}
	wg.Wait()
}

func encodeImage(filepath string) string {
	data, err := ioutil.ReadFile(filepath)
	if err != nil {
		log.Fatal(err)
	}

	encoded := base64.StdEncoding.EncodeToString(data)
	escapedEncoded := strings.ReplaceAll(encoded, "\"", "\\\"")

	return escapedEncoded
}

func fillReqBody() []byte {
	img_data, err := os.ReadFile("./coldstart.jpeg")
	if err != nil {
		log.Fatalf("Unable to read file: %s\n", err)
	}
	sEnc := b64.StdEncoding.EncodeToString(img_data)
	body := fmt.Sprintf("{\"img\":\"%s\"}", sEnc)
	return []byte(body)
}
func Request(nb chan nonBlocking) {

	client := &http.Client{}
	start := time.Now()

	// template := "http://%s/api/v1/namespaces/guest/actions/copy?blocking=true&result=true"
	// template := "http://%s/api/v1/namespaces/guest/actions/detect?blocking=true&result=true"
	// template := "http://%s/api/v1/namespaces/guest/actions/fibtest?blocking=true&result=true"

	// url := fmt.Sprintf(template, IP)
	// var jsonB = []byte("{\"input\":\"hello\"}")
	// jsonB := fillReqBody()
	var jsonB = []byte("{\"ms\":\"100\"}")

	req, err := http.NewRequest("POST", URL, bytes.NewBuffer(jsonB))
	req.Header.Add("Authorization", "Basic MjNiYzQ2YjEtNzFmNi00ZWQ1LThjNTQtODE2YWE0ZjhjNTAyOjEyM3pPM3haQ0xyTU42djJCS0sxZFhZRnBYbFBrY2NPRnFtMTJDZEFzTWdSVTRWck5aOWx5R1ZDR3VNREdJd1A=")
	req.Header.Add("Content-Type", "application/json")

	if err != nil {
		// handle error
		fmt.Println("Error")
	}
	//req.Header.Add("Authorization", "Bearer ...")
	resp, err := client.Do(req)
	elapsed := time.Since(start)

	nb <- nonBlocking{
		e2e:      elapsed,
		Response: resp,
		Error:    err,
	}
}

func HandleResponse(nb chan nonBlocking, wg *sync.WaitGroup) {

	for get := range nb {

		if get.Error != nil {
			log.Println(get.Error)
		} else {
			if get.Response.StatusCode != 200 {
				fmt.Println(get.Response.Status)
			}
			// body, err := io.ReadAll(get.Response.Body)

			// if err != nil {
			// 	fmt.Println("unable to read response body")
			// }
			// fmt.Println("body: ", string(body))
			// var objmap map[string]json.RawMessage
			// err = json.Unmarshal([]byte(body), &objmap)
			// if err != nil {
			// 	fmt.Println("unable to parse body")
			// }
			// fmt.Println(get.e2e, string(objmap["invoke_time"]))

			_, ok := get.Response.Header["Get-Candidate"]
			if ok {
				fmt.Println(get.e2e, ",", get.Response.Header.Get("Invoc-Loc"), ",", get.Response.Header.Get("Invoc-Time"), ",", get.Response.Header.Get("Get-Candidate"))
			} else {
				fmt.Println(get.e2e, ",", get.Response.Header.Get("Invoc-Loc"), ",", get.Response.Header.Get("Invoc-Time"), ",", "-1ms")
			}
			// fmt.Println(get.e2e, ",", get.Response.Header.Get("Invoc-Loc"), ",", get.Response.Header.Get("Invoc-Time"))
		}
		wg.Done()
	}

}

var numReq atomic.Int64

func RequestVideo(nb chan nonBlocking, curEncoding, prevEncoding string) {
	numReq.Add(1)
	client := &http.Client{}
	start := time.Now()

	var jsonB = fmt.Sprintf(`{"cur_frame": "%s", "prev_frame": "%s"}`, curEncoding, prevEncoding)
	reqBody := strings.NewReader(jsonB)

	req, err := http.NewRequest("POST", URL, reqBody)
	req.Header.Add("Authorization", "Basic MjNiYzQ2YjEtNzFmNi00ZWQ1LThjNTQtODE2YWE0ZjhjNTAyOjEyM3pPM3haQ0xyTU42djJCS0sxZFhZRnBYbFBrY2NPRnFtMTJDZEFzTWdSVTRWck5aOWx5R1ZDR3VNREdJd1A=")
	req.Header.Add("Content-Type", "application/json")

	if err != nil {
		// handle error
		fmt.Println("Error")
	}
	//req.Header.Add("Authorization", "Bearer ...")
	resp, err := client.Do(req)
	elapsed := time.Since(start)

	nb <- nonBlocking{
		e2e:      elapsed,
		Response: resp,
		Error:    err,
	}
}

func HandleResponseVideo(nb chan nonBlocking, wg *sync.WaitGroup) {

	for get := range nb {

		if get.Error == nil && get.Response.StatusCode != http.StatusOK {
			log.Println(get.Response.Body)
			panic(nil)
		}
		if get.Error != nil {
			log.Println(get.Error)
			log.Println(numReq.Load())
			panic(nil)
		} else {
			if get.Response.StatusCode != 200 {
				fmt.Println(get.Response.Status)
			}

			logItems := []string{
				get.e2e.String(),
				get.Response.Header.Get("Invoc-Time-filter_nocond"),
				get.Response.Header.Get("Invoc-Time-detect"),
				get.Response.Header.Get("Invoc-Time-annotate"),
				get.Response.Header.Get("Invoc-Time-sink"),
				get.Response.Header.Get("Invoc-Loc-filter_nocond"),
				get.Response.Header.Get("Invoc-Loc-detect"),
				get.Response.Header.Get("Invoc-Loc-annotate"),
				get.Response.Header.Get("Invoc-Loc-sink"),
				get.Response.Header.Get("Invoc-Queue-Depth-filter_nocond"),
				get.Response.Header.Get("Invoc-Queue-Depth-detect"),
				get.Response.Header.Get("Invoc-Queue-Depth-annotate"),
				get.Response.Header.Get("Invoc-Queue-Depth-sink"),
				time.Now().Format("15:04:05.000"),
			}
			fmt.Println(strings.Join(logItems, ","))
		}
		wg.Done()
	}

}
