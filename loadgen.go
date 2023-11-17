// adapted from https://stackoverflow.com/questions/59421516/is-there-a-non-blocking-http-client
package main

import (
	"bytes"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"sync"
	"time"

	"github.com/sbinet/npyio/npy"
)

// TODO: change to user config
const IP = "192.168.10.10:9696"

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
	tracefile := flag.String("trace", "./traffic_dur1000_lam1.0_stime10.0_rate1.0_site1.npy", "Trace file for load generation")
	flag.Parse()
	limit := *lflag

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

	go HandleResponse(nb, wg)
	for i, d := range data {
		if i >= limit {
			break
		}
		wg.Add(1)
		go Request(nb)
		time.Sleep(time.Duration(d*1e9) * time.Nanosecond)
		// time.Sleep(time.Duration(40) * time.Millisecond)
		i++
	}
	wg.Wait()
}

func Request(nb chan nonBlocking) {

	client := &http.Client{}
	start := time.Now()
	template := "http://%s/api/v1/namespaces/guest/actions/copy?blocking=true&result=true"
	url := fmt.Sprintf(template, IP)
	var jsonB = []byte("{\"input\":\"hello\"}")
	req, err := http.NewRequest("POST", url, bytes.NewBuffer(jsonB))
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
			fmt.Println(get.e2e)
		}
		wg.Done()
	}

}
