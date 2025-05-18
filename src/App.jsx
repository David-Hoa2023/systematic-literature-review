import React, { useState, useRef, useEffect } from "react";
import "./App.css";
import { RQicon } from './mysvg';
import { Button, Divider, Form, Input, Layout, Space, Table, notification, Select } from "antd"; // Added Select
import { Content, Footer, Header } from "antd/es/layout/layout";
import { SearchOutlined } from '@ant-design/icons';
import TextArea from "antd/es/input/TextArea";
import FullPageLoader from "./FullPageLoader";
import { answers as answersColumns, columns as RQBcolumns, filterColumns, paperColumns } from "./columns"; // Renamed 'columns' to 'RQBcolumns' to avoid conflict

const { Option } = Select; // For Select options

function App() {
    const [loading, setLoading] = useState(false);
    const contentRef = useRef();

    // State for inputs
    const [name, setName] = useState("My work aims to systematically identify and analyze the literature on Large language models in software development"); // Default objective
    const [noOfQuestion, setNoOfQuestions] = useState(2);
    const [start_year, setstartYear] = useState(new Date().getFullYear() - 1); // Default to previous year
    const [limitPaper, setLimitPaper] = useState(10);
    
    // State for model selection
    const [selectedModel, setSelectedModel] = useState("gpt-3.5-turbo"); // Default model

    // State for API responses and data flow
    const [researchQuestionApiResponse, setResearchQuestionApiResponse] = useState([]); // {question: string, purpose: string}[]
    const [researchQuestions, setResearchQuestions] = useState([]); // string[] derived from researchQuestionApiResponse
    const [searchString, setSearchString] = useState('');
    const [papersData, setPapersData] = useState([]); // Raw papers from Scopus
    const [papersFilterData, setPapersFilterData] = useState([]); // Papers selected by user or filtered by LLM
    const [ansWithQuestions, setAnsWithQuestionsData] = useState([]); // {question: string, answer: string}[]
    const [summary, setSummary] = useState(''); // Abstract summary
    const [introSummary, setIntroSummary] = useState(''); // Introduction summary
    // const [downloadlink, setDownloadLink] = useState(''); // Not used, direct download implemented

    const availableModels = [
        { value: "gpt-3.5-turbo", label: "GPT-3.5 Turbo (OpenAI)" },
        { value: "gpt-4-turbo-preview", label: "GPT-4 Turbo Preview (OpenAI)" },
        { value: "gpt-4.1", label: "GPT-4.1 (OpenAI - Hypothetical)" },
        { value: "deepseek-chat", label: "DeepSeek Chat (General)" }, // Example specific model
        { value: "deepseek-coder", label: "DeepSeek Coder (Specific)" }, // Example specific model
        // !!! IMPORTANT: Replace "deepseek-chat", "deepseek-coder" with actual, valid DeepSeek model identifiers !!!
        // Consult DeepSeek documentation for available model names.
        // The backend `agents.py` uses `model_name.startswith("deepseek")` for routing.
    ];

    const scrollToBottom = () => {
        const elem = document.getElementById("mainContainer");
        if (elem) {
            setTimeout(() => {
                elem.scroll(0, elem.scrollHeight);
            }, 300);
        }
    };

    // Effect to update researchQuestions (string array) when researchQuestionApiResponse changes
    useEffect(() => {
        if (researchQuestionApiResponse && researchQuestionApiResponse.length > 0) {
            setResearchQuestions(researchQuestionApiResponse.map(item => item.question));
        } else {
            setResearchQuestions([]);
        }
    }, [researchQuestionApiResponse]);


    const handleApiCall = async (endpoint, payload, successMessage, setDataCallback) => {
        setLoading(true);
        try {
            const response = await fetch(endpoint, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ ...payload, model_name: selectedModel }), // Always include selectedModel
            });
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ error: "Failed to parse error response" }));
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }
            const message = await response.json();
            if (message.error) { // Check for backend-relayed error
                 throw new Error(message.error.details || message.error);
            }

            if (setDataCallback) setDataCallback(message);
            
            notification.success({ message: successMessage });
            scrollToBottom();
        } catch (error) {
            console.error(`Error in ${successMessage.toLowerCase().replace(/\s+/g, '_')}:`, error);
            notification.error({ message: "Operation Failed", description: error.message });
        } finally {
            setLoading(false);
        }
    };
    
    const handleSubmitObjective = (e) => {
        e.preventDefault();
        handleApiCall("/api/generate_research_questions_and_purpose",
            { objective: name, num_questions: noOfQuestion },
            "Research Questions Generated",
            (data) => {
                // data.research_questions is {research_questions: [{question, purpose}]}
                if (data.research_questions && data.research_questions.research_questions) {
                     setResearchQuestionApiResponse(data.research_questions.research_questions.map((item, index) => ({ ...item, key: index })));
                } else if (data.research_questions) { // If structure is simpler like {question, purpose}[]
                    setResearchQuestionApiResponse(data.research_questions.map((item, index) => ({ ...item, key: index })));
                } else {
                    setResearchQuestionApiResponse([]);
                    notification.warn({message: "No research questions returned or unexpected format."})
                }
            }
        );
    };

    const generateSearchString = (e) => {
        e.preventDefault();
        if (!researchQuestions || researchQuestions.length === 0) {
            notification.warn({ message: "Please generate research questions first." });
            return;
        }
        handleApiCall("/api/generate_search_string",
            { objective: name, research_questions: researchQuestions },
            "Search String Generated",
            (data) => setSearchString(data.search_string)
        );
    };

    const fetchAndSavePapers = (e) => {
        e.preventDefault();
        if (!searchString) {
            notification.warn({ message: "Please generate a search string first." });
            return;
        }
        const source = e.target.dataset?.source || 'scopus';
        handleApiCall("/api/search_papers",
            { 
                search_string: searchString, 
                start_year: start_year, 
                limit: limitPaper,
                source: source
            },
            `Papers Found from ${source === 'semanticscholar' ? 'Semantic Scholar' : 'Scopus'}`,
            (data) => setPapersData(data || []) // data is expected to be an array of papers
        );
    };
    
    const handleCheckboxChange = (record) => {
        setPapersFilterData(prev => {
            const newSelection = [...prev];
            const index = newSelection.findIndex(item => item.identifier === record.identifier); // Assuming 'identifier' or 'doi' as unique key
            if (index > -1) {
                newSelection.splice(index, 1);
            } else {
                newSelection.push(record);
            }
            return newSelection;
        });
    };

    const fetchAndFilterPapers = (e) => {
        e.preventDefault();
        if (!papersData || papersData.length === 0) {
            notification.warn({ message: "Please fetch papers first." });
            return;
        }
        handleApiCall("/api/filter_papers",
            { search_string: searchString, papers: papersData }, // Pass all fetched papers for LLM filtering
            "Papers Filtered by LLM",
            (data) => {
                // data.filtered_papers contains papers LLM deemed relevant
                // We should replace papersFilterData with these, or merge if user selections are also to be kept
                // For now, let's assume LLM filter overrides manual selection for this step.
                setPapersFilterData(data.filtered_papers || []);
                if (data.filtered_papers && data.filtered_papers.length < papersData.length) {
                    notification.info({ message: `Filtered down to ${data.filtered_papers.length} relevant papers.`});
                } else if (data.filtered_papers) {
                     notification.info({ message: `All ${data.filtered_papers.length} papers deemed relevant.`});
                }
            }
        );
    };
    
    const generateAnswers = (e) => { // Renamed from ansWithQuestionsData
        e.preventDefault();
        if (!papersFilterData || papersFilterData.length === 0) {
            notification.warn({ message: "Please filter or select papers first." });
            return;
        }
        if (!researchQuestions || researchQuestions.length === 0) {
            notification.warn({ message: "No research questions to answer." });
            return;
        }
        handleApiCall("/api/answer_question",
            { questions: researchQuestions, papers_info: papersFilterData },
            "Answers Generated",
            (data) => setAnsWithQuestionsData(data.answers || [])
        );
    };

    const generateSummaryAbstract = (e) => {
        e.preventDefault();
        handleApiCall("/api/generate-summary-abstract",
            { research_questions: researchQuestions, objective: name, search_string: searchString },
            "Summary Abstract Generated",
            (data) => setSummary(data.summary_abstract)
        );
    };

    const generateIntroductionSummary = (e) => { // Renamed from introductionSummary
        e.preventDefault();
        handleApiCall("/api/generate-introduction-summary",
            { 
                research_questions: researchQuestions, 
                objective: name, 
                search_string: searchString,
                total_papers: papersData, // Send all initially fetched papers
                filtered_papers: papersFilterData, // Send filtered/selected papers
                answers: ansWithQuestions
            },
            "Introduction Summary Generated",
            (data) => setIntroSummary(data.introduction_summary)
        );
    };

    const generateAllSummaryAndDownload = async (e) => { // Renamed from generateAllSummary
        e.preventDefault();
        setLoading(true);
        try {
            const response = await fetch("/api/generate-summary-all", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    abstract_summary: summary,
                    intro_summary: introSummary,
                    conclusion_summary: summary, // Assuming abstract can serve as conclusion basis, or generate separately
                    model_name: selectedModel // Though this endpoint itself doesn't use LLM, good to be consistent if it might in future
                }),
            });
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ error: "Failed to parse error response" }));
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }
            const blob = await response.blob();
            const contentDisposition = response.headers.get('Content-Disposition');
            const filename = contentDisposition ? contentDisposition.split('filename=')[1].replace(/"/g, '') : 'paper_summary.tex';
            
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', filename);
            document.body.appendChild(link);
            link.click();
            link.remove(); // Clean up the link
            window.URL.revokeObjectURL(url); // Clean up the blob URL
            notification.success({ message: "LaTeX Paper Summary Downloading" });

        } catch (error) {
            console.error("Error generating LaTeX summary:", error);
            notification.error({ message: "LaTeX Generation Failed", description: error.message });
        } finally {
            setLoading(false);
        }
    };
    
    const handleResearchQuestionsTextareaChange = (event) => {
        const newText = event.target.value;
        // Update researchQuestionApiResponse to keep it in sync if questions are edited
        // This is a bit complex as purposes are tied. For simplicity, this just updates the string array.
        // A more robust solution would involve updating the researchQuestionApiResponse state.
        const updatedQuestions = newText.split('\n')
            .map(line => line.replace(/^Question \d+: /gm, '').trim())
            .filter(q => q.length > 0);
        setResearchQuestions(updatedQuestions);

        // Optionally, update researchQuestionApiResponse if you want to keep purposes aligned
        // This is a simplified update, assuming order matches.
        setResearchQuestionApiResponse(prev => 
            updatedQuestions.map((q, index) => ({
                question: q,
                purpose: prev[index] ? prev[index].purpose : "Purpose needs review after edit",
                key: prev[index] ? prev[index].key : index
            }))
        );
    };

    const handleSearchStringChange = (event) => {
        setSearchString(event.target.value);
    };

    return (
        <Layout>
            <Header style={{ backgroundColor: "#f3fff3" }} >
                <div style={{ display: "flex", flexDirection: "row", justifyContent: "space-between", alignItems: "center", height: "100%"}}>
                    <RQicon width={"50px"} height={"50px"} />
                    <div style={{ fontSize: "20px", color: "black" }}>
                        <strong>Literature Review Automation</strong>
                    </div>
                    <div style={{width: "50px"}}> {/* Placeholder for balance */}</div>
                </div>
            </Header>
            <Layout>
                <Content>
                    {loading && <FullPageLoader/>}
                    <div
                        id="mainContainer" 
                        style={{
                            lineHeight: "initial", // Reset line height for content
                            display: "flex",
                            flexDirection: "column",
                            alignItems: "center",
                            overflowY: "auto",
                            height: "calc(100vh - 64px - 48px)", // Adjust for header and footer
                            padding: "20px",
                            gap: "15px" // Adds space between direct children divs
                        }}
                        ref={contentRef}
                    >
                        {/* Objective Input and Model Selection Section */}
                        <div style={{ width: "80vw", border: '1px solid #ccc', padding: 15, borderRadius: "10px", background: '#fff' }}>
                            <h5>Hello, I am your Agent. Enter Your Research Objective and Select a Model.</h5>
                            <Form layout="vertical" style={{ width: "100%" }}>
                                <Form.Item label="Research Objective" style={{ marginBottom: '10px' }}>
                                    <Input
                                        placeholder="e.g., Analyze the impact of AI on software testing..."
                                        value={name}
                                        onChange={(e) => setName(e.target.value)}
                                    />
                                </Form.Item>
                                <Space style={{display: 'flex'}} align="baseline">
                                    <Form.Item label="Number of Research Questions" style={{ flexGrow: 1, marginBottom: '10px'  }}>
                                        <Input
                                            placeholder="e.g., 3"
                                            min={1}
                                            max={10}
                                            value={noOfQuestion}
                                            onChange={(e) => setNoOfQuestions(Math.max(1, parseInt(e.target.value) || 1))}
                                            type="number"
                                        />
                                    </Form.Item>
                                    <Form.Item label="Select AI Model" style={{ flexGrow: 1, marginBottom: '10px'  }}>
                                        <Select
                                            value={selectedModel}
                                            onChange={(value) => setSelectedModel(value)}
                                            style={{ width: '100%' }}
                                        >
                                            {availableModels.map(model => (
                                                <Option key={model.value} value={model.value}>
                                                    {model.label}
                                                </Option>
                                            ))}
                                        </Select>
                                    </Form.Item>
                                </Space>
                                <Button
                                    type="primary"
                                    icon={<SearchOutlined />}
                                    onClick={handleSubmitObjective}
                                    block
                                >
                                    Generate Research Questions & Purpose
                                </Button>
                            </Form>
                        </div>

                        {/* Research Questions Display */}
                        {researchQuestionApiResponse && researchQuestionApiResponse.length > 0 && (
                            <div style={{ width: "80vw", border: '1px solid #ccc', padding: 10, borderRadius: "10px", background: '#fff' }}>
                                <Table title={() => <strong>Generated Research Questions & Purposes</strong>} scroll={{ x: 1000, y: 300 }} dataSource={researchQuestionApiResponse} columns={RQBcolumns} pagination={false} size="small" />
                            </div>
                        )}

                        {/* Editable Research Questions & Search String Generation */}
                        {researchQuestions && researchQuestions.length > 0 && (
                            <div style={{ width: "80vw", border: '1px solid #ccc', padding: 15, borderRadius: "10px", background: '#fff' }}>
                                <Form layout="vertical">
                                    <Form.Item label="Edit Research Questions (one per line):">
                                        <TextArea 
                                            style={{ width: "100%" }} 
                                            onChange={handleResearchQuestionsTextareaChange} 
                                            value={researchQuestions.map((question, index) => `Question ${index + 1}: ${question}`).join('\n')} 
                                            rows={Math.max(3, researchQuestions.length)} 
                                            placeholder="Edit your questions here. The 'Question X:' prefix is for display and will be handled."
                                        />
                                    </Form.Item>
                                    <Button type="primary" onClick={generateSearchString} block>Create Search String</Button>
                                </Form>
                            </div>
                        )}
                        
                        {/* Search String Display & Paper Fetching */}
                        {searchString && (
                            <div style={{ width: "80vw", border: '1px solid #ccc', padding: 15, borderRadius: "10px", background: '#fff' }}>
                                <Form layout="vertical">
                                    <Form.Item label="Generated Search String:">
                                        <TextArea value={searchString} onChange={handleSearchStringChange} rows={3} style={{ width: "100%" }} />
                                    </Form.Item>
                                    <Space style={{display: 'flex'}} align="baseline">
                                        <Form.Item label="Start Year (Scopus)" style={{flexGrow: 1, marginBottom: '10px'}}>
                                            <Input type="number" max={new Date().getFullYear()} min={1900} value={start_year} onChange={(e) => setstartYear(e.target.value)} />
                                        </Form.Item>
                                        <Form.Item label="Number of Papers to Fetch (Max 15-20 recommended)" style={{flexGrow: 1, marginBottom: '10px'}}>
                                            <Input type="number" max={25} min={1} value={limitPaper} onChange={(e)=> setLimitPaper(e.target.value)}  placeholder="e.g., 10"/>
                                        </Form.Item>
                                    </Space>
                                    <Space style={{ width: '100%', marginBottom: 16 }} direction="vertical">
                                        <Button type="primary" onClick={fetchAndSavePapers} block>Fetch Papers from Scopus</Button>
                                        <Button 
                                            type="primary" 
                                            onClick={(e) => {
                                                const syntheticEvent = { ...e };
                                                syntheticEvent.target = { ...e.target, dataset: { source: 'semanticscholar' } };
                                                fetchAndSavePapers(syntheticEvent);
                                            }} 
                                            block
                                            style={{ 
                                                marginTop: '10px',
                                                backgroundColor: '#28a745',
                                                borderColor: '#28a745'
                                            }}
                                        >
                                            Fetch Papers from Semantic Scholar
                                        </Button>
                                    </Space>
                                </Form>
                            </div>
                        )}

                        {/* Papers Display & Filtering */}
                        {papersData && papersData.length > 0 && (
                            <div style={{ width: "80vw", border: '1px solid #ccc', padding: 10, borderRadius: "10px", background: '#fff' }}>
                                <Table 
                                    title={() => <strong>Fetched Papers (Select relevant ones or use AI filter)</strong>}
                                    scroll={{ x: 1500, y: 400 }} 
                                    dataSource={papersData.map(p => ({...p, key: p.identifier || p.doi || p.title }))} // Ensure unique key
                                    columns={paperColumns(papersFilterData, handleCheckboxChange)} 
                                    pagination={{ pageSize: 5 }} 
                                    size="small" 
                                />
                                <Button type="primary" onClick={fetchAndFilterPapers} style={{ marginTop: "10px", width: "100%" }}>Filter with AI ({selectedModel})</Button>
                            </div>
                        )}

                        {/* Filtered/Selected Papers Display & Answer Generation */}
                        {papersFilterData && papersFilterData.length > 0 && (
                             <div style={{ width: "80vw", border: '1px solid #ccc', padding: 10, borderRadius: "10px", background: '#fff' }}>
                                <Table 
                                    title={() => <strong>Selected/AI-Filtered Papers for Analysis</strong>}
                                    scroll={{ x: 1500, y: 400 }} 
                                    dataSource={papersFilterData.map(p => ({...p, key: p.identifier || p.doi || p.title }))} // Ensure unique key
                                    columns={filterColumns} // filterColumns doesn't need checkbox handling
                                    pagination={{ pageSize: 5 }} 
                                    size="small" 
                                />
                                <Button type="primary" onClick={generateAnswers} style={{ marginTop: "10px", width: "100%" }}>Find Answers using AI ({selectedModel})</Button>
                            </div>
                        )}

                        {/* Answers Display & Summary Generation */}
                        {ansWithQuestions && ansWithQuestions.length > 0 && (
                            <div style={{ width: "80vw", border: '1px solid #ccc', padding: 10, borderRadius: "10px", background: '#fff' }}>
                                <Table 
                                    title={() => <strong>Generated Answers</strong>}
                                    dataSource={ansWithQuestions.map((a, i) => ({...a, key: i}))} 
                                    columns={answersColumns} 
                                    pagination={false} 
                                    size="small" 
                                />
                                <Button type="primary" onClick={generateSummaryAbstract} style={{ marginTop: "10px", width: "100%" }}>Generate Summary Abstract ({selectedModel})</Button>
                            </div>
                        )}

                        {/* Abstract Summary Display & Introduction Generation */}
                        {summary && (
                            <div style={{ width: "80vw", border: '1px solid #ccc', padding: 15, borderRadius: "10px", background: '#fff' }}>
                                <Form layout="vertical">
                                    <Form.Item label="Generated Summary Abstract:">
                                        <TextArea value={summary} onChange={(e)=> setSummary(e.target.value)} rows={7} style={{ width: "100%" }} />
                                    </Form.Item>
                                    <Button type="primary" onClick={generateIntroductionSummary} block>Generate Introduction Summary ({selectedModel})</Button>
                                </Form>
                            </div>
                        )}
                        
                        {/* Introduction Summary Display & Final Paper Generation */}
                        {introSummary && (
                            <div style={{ width: "80vw", border: '1px solid #ccc', padding: 15, borderRadius: "10px", background: '#fff' }}>
                                <Form layout="vertical">
                                    <Form.Item label="Generated Introduction Summary:">
                                        <TextArea value={introSummary} onChange={(e)=> setIntroSummary(e.target.value)} rows={7} style={{ width: "100%" }} />
                                    </Form.Item>
                                    <Button type="primary" onClick={generateAllSummaryAndDownload} block>Create & Download LaTeX Paper Summary</Button>
                                </Form>
                            </div>
                        )}
                    </div>
                </Content>
            </Layout>
            <Footer style={{ textAlign: 'center', backgroundColor: '#f0f2f5', padding: '10px 0', lineHeight: 'normal' }} className="footerFixed">
                   <p style={{margin:0}}>&copy; {new Date().getFullYear()} SLR Automation Tool. All rights reserved.</p>
            </Footer>
        </Layout>
    );
}

export default App;

