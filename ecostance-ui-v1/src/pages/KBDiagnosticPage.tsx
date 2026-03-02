import React, { useState } from 'react';
import { Button } from '../components/ui/Button';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';
import { knowledgeBaseAPI, getAccessToken } from '../services/api';

const KBDiagnosticPage: React.FC = () => {
  const [diagnosticResults, setDiagnosticResults] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const runDiagnostics = async () => {
    setLoading(true);
    const results: any = {
      timestamp: new Date().toISOString(),
      checks: [],
    };

    // Check 1: Token exists
    const token = getAccessToken();
    results.checks.push({
      name: 'Access Token',
      status: token ? 'PASS' : 'FAIL',
      details: token ? `Token exists (${token.substring(0, 20)}...)` : 'No token found',
    });

    // Check 2: API Base URL
    const apiBaseUrl = import.meta.env.VITE_API_BASE_URL;
    results.checks.push({
      name: 'API Base URL',
      status: 'INFO',
      details: apiBaseUrl,
    });

    // Check 3: Try to fetch knowledge bases
    try {
      console.log('Attempting to fetch knowledge bases...');
      const response = await knowledgeBaseAPI.list();
      console.log('Raw response:', response);

      results.checks.push({
        name: 'Knowledge Base API Call',
        status: 'PASS',
        details: `Received response: ${JSON.stringify(response, null, 2)}`,
        data: response,
      });
    } catch (error: any) {
      console.error('KB API Error:', error);
      results.checks.push({
        name: 'Knowledge Base API Call',
        status: 'FAIL',
        details: `Error: ${error.message}`,
        error: error.toString(),
      });
    }

    // Check 4: Try direct fetch
    try {
      const directResponse = await fetch(`${apiBaseUrl}/manage/knowledge-bases/`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      });

      const directData = await directResponse.json();

      results.checks.push({
        name: 'Direct Fetch Test',
        status: directResponse.ok ? 'PASS' : 'FAIL',
        details: `Status: ${directResponse.status} ${directResponse.statusText}`,
        data: directData,
      });
    } catch (error: any) {
      results.checks.push({
        name: 'Direct Fetch Test',
        status: 'FAIL',
        details: `Error: ${error.message}`,
      });
    }

    setDiagnosticResults(results);
    setLoading(false);
  };

  return (
    <div className="w-full max-w-4xl mx-auto p-6">
      <Card>
        <CardHeader>
          <CardTitle>Knowledge Base Diagnostic Tool</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <Button onClick={runDiagnostics} disabled={loading}>
              {loading ? 'Running Diagnostics...' : 'Run Diagnostics'}
            </Button>

            {diagnosticResults && (
              <div className="mt-6 space-y-4">
                <div className="text-sm text-gray-500">
                  Test run at: {new Date(diagnosticResults.timestamp).toLocaleString()}
                </div>

                {diagnosticResults.checks.map((check: any, index: number) => (
                  <Card key={index} className={
                    check.status === 'PASS' ? 'border-green-500' :
                      check.status === 'FAIL' ? 'border-red-500' :
                        'border-blue-500'
                  }>
                    <CardHeader>
                      <CardTitle className="text-base flex items-center gap-2">
                        <span className={
                          check.status === 'PASS' ? 'text-green-600' :
                            check.status === 'FAIL' ? 'text-red-600' :
                              'text-blue-600'
                        }>
                          {check.status === 'PASS' ? '✓' : check.status === 'FAIL' ? '✗' : 'ℹ'}
                        </span>
                        {check.name}
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        <div className="text-sm">{check.details}</div>
                        {check.data && (
                          <pre className="bg-gray-100 p-3 rounded text-xs overflow-auto max-h-96">
                            {JSON.stringify(check.data, null, 2)}
                          </pre>
                        )}
                        {check.error && (
                          <pre className="bg-red-50 p-3 rounded text-xs overflow-auto">
                            {check.error}
                          </pre>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default KBDiagnosticPage;
