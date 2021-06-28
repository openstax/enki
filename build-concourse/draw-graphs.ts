import * as path from "path";
import { digraph, attribute, Dot } from "ts-graphviz";
import { exportToFile } from "@ts-graphviz/node";
import { GIT_PDF_STEPS, GIT_WEB_STEPS, ARCHIVE_PDF_STEPS, ARCHIVE_GDOC_STEPS, ARCHIVE_WEB_STEPS_WITH_DEQUEUE_AND_UPLOAD, Step } from './step-definitions'

const DIRS_TO_SKIP = new Set()
DIRS_TO_SKIP.add('book')

function ensureEdge<K, V>(map: Map<K,V>, key: K, value: () => V) {
    if (!map.has(key)) {
        const v = value()
        map.set(key, v)
        return v
    }
    return map.get(key)
}

type DirInOut = {
    inputs: string[]
    outputs: string[]
}
function initValue(): DirInOut {
    return {inputs: [], outputs: []}
}

async function buildChart(steps: Step[], destFilename: string) {
    console.log('Generating image file:', destFilename)
    // Build all the nodes (Step)
    const nodes: string[] = []

    // Build all the edges (Directory)
    const edges = new Map<string, DirInOut>()
    const prevOutputs = new Map<string, string>()
    steps.forEach(step => {
        nodes.push(step.name)
        step.inputs.forEach(dir => {
            if (DIRS_TO_SKIP.has(dir)) { return }
            ensureEdge(edges, dir, initValue).inputs.push(step.name)
        })
        step.outputs.forEach(dir => {
            if (DIRS_TO_SKIP.has(dir)) { return }
            ensureEdge(edges, dir, initValue).outputs.push(step.name)
        })
    })

    const G = digraph("G", (g) => {
        const nodeMap = new Map<string, Dot>()
        nodes.forEach(n => nodeMap.set(n, g.node(n)))

        Array.from(edges.entries()).forEach(([edgeLabel, {inputs, outputs}]) => {
            inputs.forEach(i => {
                outputs.forEach(o => {
                    if (o !== i) {
                        g.edge([o,i], {
                            [attribute.label]: edgeLabel
                        })
                    }
                })
            })
        });
      });
      
      
      await exportToFile(G, {
        format: "png",
        output: path.resolve(destFilename),
      });
}


(async function buildCharts() {
    await buildChart(GIT_PDF_STEPS, './graphs/git-pdf.png')
    await buildChart(GIT_WEB_STEPS, './graphs/git-web.png')
    await buildChart(ARCHIVE_PDF_STEPS, './graphs/archive-pdf.png')
    await buildChart(ARCHIVE_WEB_STEPS_WITH_DEQUEUE_AND_UPLOAD, './graphs/archive-web.png')
    await buildChart(ARCHIVE_GDOC_STEPS, './graphs/archive-gdocs.png')
})().then(null, console.error)